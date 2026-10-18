"""Bounded FHIR R4 JSON/XML input and server-controlled REST retrieval."""
import importlib
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import urljoin, urlsplit

import requests
from django.conf import settings

FHIR_NS = "http://hl7.org/fhir"
MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 20
MAX_RESOURCES = 1000
MAX_PAGES = 10


def _resource_class(name):
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]+", name):
        raise ValueError("無法辨識 FHIR R4 resourceType。")
    try:
        return getattr(importlib.import_module("fhirclient.models." + name.lower()), name)
    except (ImportError, AttributeError):
        raise ValueError("不支援此 FHIR R4 XML 資源類型。") from None


def _xml_object(element, cls, depth=0, resource=False):
    if depth > 64:
        raise ValueError("FHIR XML 巢狀層級過深。")
    props = {prop[1]: prop for prop in cls().elementProperties()}
    output = {"resourceType": element.tag.split("}")[-1]} if resource else {}
    for attr, value in element.attrib.items():
        if attr not in {"id", "url"} or (resource and attr == "id"):
            raise ValueError("FHIR XML 包含不支援的屬性。")
        output[attr] = value
    seen = set()
    for child in element:
        namespace, _, name = child.tag[1:].partition("}") if child.tag.startswith("{") else ("", "", child.tag)
        if namespace == "http://www.w3.org/1999/xhtml" and name == "div" and "div" in props:
            output["div"] = ET.tostring(child, encoding="unicode")
            continue
        if namespace != FHIR_NS or name not in props:
            raise ValueError("FHIR XML 包含未知欄位或不正確的 namespace。")
        _, _, value_type, repeated, _, _ = props[name]
        if not repeated and name in seen:
            raise ValueError("FHIR XML 的單值欄位重複出現。")
        seen.add(name)
        primitive = value_type in (str, bool, int, float) or value_type.__name__ in {"FHIRDate", "FHIRDateTime", "FHIRInstant"}
        if primitive:
            allowed = {"value", "id"}
            if set(child.attrib) - allowed:
                raise ValueError("FHIR primitive 包含不支援的屬性。")
            value = child.attrib.get("value")
            if value is not None:
                if value_type is bool:
                    if value not in {"true", "false"}:
                        raise ValueError("FHIR boolean 必須為 true 或 false。")
                    value = value == "true"
                elif value_type is int:
                    if not re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
                        raise ValueError("FHIR integer 格式錯誤。")
                    value = int(value)
                elif value_type is float:
                    if not re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?", value):
                        raise ValueError("FHIR decimal 格式錯誤。")
                    if not math.isfinite(float(value)):
                        raise ValueError("FHIR decimal 必須為有限數值。")
                    # Preserve the same integer/fraction representation as JSON decoding.
                    # Otherwise XML value="0" becomes 0.0 and creates a false merge conflict.
                    value = json.loads(value)
            metadata = {}
            if "id" in child.attrib:
                metadata["id"] = child.attrib["id"]
            for extension in child:
                if extension.tag != "{" + FHIR_NS + "}extension":
                    raise ValueError("FHIR primitive 子元素必須為 extension。")
                from fhirclient.models.extension import Extension
                metadata.setdefault("extension", []).append(_xml_object(extension, Extension, depth + 1))
            if value is None and not metadata:
                raise ValueError("FHIR primitive 不可為空。")
            if repeated:
                output.setdefault(name, []).append(value)
                # Null placeholders preserve alignment for primitive extensions.
                output.setdefault("_" + name, []).append(metadata or None)
            elif value is not None:
                output[name] = value
            if metadata and not repeated:
                output["_" + name] = metadata
        elif value_type.__name__ == "Resource":
            if len(child) != 1:
                raise ValueError("FHIR resource wrapper 必須包含一個資源。")
            nested = child[0]
            nested_name = nested.tag.removeprefix("{" + FHIR_NS + "}")
            value = _xml_object(nested, _resource_class(nested_name), depth + 1, resource=True)
            if repeated:
                output.setdefault(name, []).append(value)
            else:
                output[name] = value
        else:
            value = _xml_object(child, value_type, depth + 1)
            if repeated:
                output.setdefault(name, []).append(value)
            else:
                output[name] = value
    for key in list(output):
        if key.startswith("_") and isinstance(output[key], list) and not any(output[key]):
            del output[key]
    return output


def decode_fhir(data, data_format="auto"):
    if isinstance(data, dict):
        try:
            size = len(json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        except (ValueError, RecursionError):
            raise ValueError("FHIR JSON 結構或數值格式錯誤。") from None
        if size > MAX_BYTES:
            raise ValueError("FHIR 輸入總大小不得超過 10 MB。")
        return data
    if isinstance(data, bytes):
        if len(data) > MAX_BYTES:
            raise ValueError("FHIR 輸入總大小不得超過 10 MB。")
        try:
            data = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("FHIR 檔案必須使用 UTF-8 編碼。") from None
    if not isinstance(data, str) or len(data.encode("utf-8")) > MAX_BYTES:
        raise ValueError("請提供 10 MB 以內的 FHIR JSON 或 XML。")
    data = data.lstrip("\ufeff \r\n\t")
    if data_format not in {"auto", "json", "xml"}:
        raise ValueError("FHIR 格式必須為 auto、json 或 xml。")
    is_xml = data_format == "xml" or (data_format == "auto" and data.startswith("<"))
    if not is_xml:
        try:
            return json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("JSON 不可包含非有限數值。")))
        except (json.JSONDecodeError, RecursionError):
            raise ValueError("FHIR JSON 格式錯誤。") from None
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", data, re.I):
        raise ValueError("FHIR XML 不允許 DTD 或 ENTITY。")
    try:
        element = ET.fromstring(data)
        if not element.tag.startswith("{" + FHIR_NS + "}"):
            raise ValueError("FHIR XML 必須使用 http://hl7.org/fhir namespace。")
        name = element.tag.split("}")[-1]
        return _xml_object(element, _resource_class(name), resource=True)
    except (ET.ParseError, RecursionError):
        raise ValueError("FHIR XML 格式錯誤。") from None


def merge_fhir(documents):
    entries = []
    identities = {}
    full_urls = {}
    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get("resourceType"), str):
            raise ValueError("請提供具有 resourceType 的 FHIR resource 或 Bundle。")
        if document["resourceType"] == "OperationOutcome":
            raise ValueError("來源回傳 OperationOutcome，未提供可匯入的臨床資源。")
        incoming = document.get("entry") if document["resourceType"] == "Bundle" else [{"resource": document}]
        if not isinstance(incoming, list) or not incoming:
            raise ValueError("Bundle 必須提供非空的 entry 資源陣列。")
        for entry in incoming:
            resource = entry.get("resource") if isinstance(entry, dict) else None
            if not isinstance(resource, dict) or not resource.get("resourceType"):
                raise ValueError("每個 entry 都必須包含 resource 與 resourceType。")
            key = (resource["resourceType"], resource.get("id"))
            canonical = json.dumps(resource, sort_keys=True, ensure_ascii=False, allow_nan=False)
            full_url = entry.get("fullUrl")
            if full_url and full_url in full_urls and full_urls[full_url] != (key, canonical):
                raise ValueError("多份資料包含衝突的 fullUrl。")
            if full_url:
                full_urls[full_url] = (key, canonical)
            if key[1] and key in identities:
                prior, prior_url = identities[key]
                if prior != canonical or (prior_url and full_url and prior_url != full_url):
                    raise ValueError("同一 resourceType/id 出現不同內容或 fullUrl，請先處理來源衝突。")
                if full_url and not prior_url:
                    next(item for item in entries if (item["resource"].get("resourceType"), item["resource"].get("id")) == key)["fullUrl"] = full_url
                    identities[key] = (prior, full_url)
                continue
            identities[key] = (canonical, full_url)
            normalized = {"resource": resource}
            if full_url:
                normalized["fullUrl"] = full_url
            entries.append(normalized)
            if len(entries) > MAX_RESOURCES:
                raise ValueError("單次最多匯入 1000 個 FHIR 資源。")
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def summarize(bundle):
    counts = Counter(entry["resource"]["resourceType"] for entry in bundle["entry"])
    return {"totalResources": sum(counts.values()), "byType": dict(counts)}


def _origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("請提供不含帳密或 fragment 的 HTTP(S) FHIR URL。")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        raise ValueError("FHIR URL port 格式錯誤。") from None
    return parsed.scheme.lower(), parsed.hostname.lower(), port


def fetch_rest_fhir(url, token=""):
    origin = _origin(url)
    allowed = {_origin(value) for value in getattr(settings, "FHIR_IMPORT_ALLOWED_ORIGINS", [])}
    if origin not in allowed:
        raise ValueError("此 FHIR API 來源尚未啟用，請由管理員設定允許的來源。")
    if token and (len(token) > 8192 or any(char.isspace() for char in token)):
        raise ValueError("Access token 格式錯誤。")
    if token and origin[0] != "https" and origin[1] not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("外部 API 傳送 Access token 必須使用 HTTPS。")
    headers = {"Accept": "application/fhir+json, application/fhir+xml;q=0.9"}
    if token:
        headers["Authorization"] = "Bearer " + token
    documents, visited, total_bytes = [], set(), 0
    with requests.Session() as session:
        session.trust_env = False
        for _ in range(MAX_PAGES):
            if url in visited or _origin(url) != origin:
                raise ValueError("FHIR 分頁出現循環或跨來源連結。")
            visited.add(url)
            try:
                with session.get(url, headers=headers, timeout=(5, 15), stream=True, allow_redirects=False) as response:
                    if response.status_code != 200:
                        raise ValueError(f"FHIR API 讀取失敗（HTTP {response.status_code}），未匯入資料。")
                    chunks = []
                    for chunk in response.iter_content(65536):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_BYTES:
                            raise ValueError("FHIR API 回傳總大小超過 10 MB，未匯入資料。")
                        chunks.append(chunk)
                    document = decode_fhir(b"".join(chunks))
            except requests.RequestException:
                raise ValueError("FHIR API 連線失敗或逾時，未匯入資料。") from None
            documents.append(document)
            merge_fhir(documents)
            links = document.get("link", []) if isinstance(document, dict) else []
            next_links = [link.get("url") for link in links if link.get("relation") == "next"]
            if not next_links:
                return merge_fhir(documents)
            if len(next_links) != 1 or not isinstance(next_links[0], str):
                raise ValueError("FHIR 分頁連結格式錯誤。")
            url = urljoin(url, next_links[0])
        raise ValueError("FHIR API 超過 10 頁，請縮小查詢範圍；未匯入資料。")


def request_fhir_payload(request):
    files = request.FILES.getlist("files") or request.FILES.getlist("file")
    if files:
        if len(files) > MAX_FILES or sum(file.size for file in files) > MAX_BYTES:
            raise ValueError("單次最多 20 個檔案，總大小不得超過 10 MB。")
        documents = []
        for file in files:
            try:
                documents.append(decode_fhir(file.read(MAX_BYTES + 1)))
            except ValueError as error:
                raise ValueError(f"{file.name}: {error}") from None
        return merge_fhir(documents)
    if request.data.get("url"):
        return fetch_rest_fhir(str(request.data["url"]), str(request.data.get("access_token") or ""))
    return merge_fhir([decode_fhir(request.data.get("fhir_data"), request.data.get("format") or "auto")])
