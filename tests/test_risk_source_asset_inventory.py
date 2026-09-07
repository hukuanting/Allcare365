import json
import zipfile

from openpyxl import Workbook

from services.disease_risk_engine.source_asset_inventory import build_source_manifest


def _minimal_docx(path):
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:r><w:t>Risk = exp(beta * age)</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>coefficient</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      </w:body>
    </w:document>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" TargetMode="External" Target="https://doi.org/10.1/test" Type="test"/>
    </Relationships>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", relationships)


def test_source_manifest_hashes_every_asset_and_extracts_formula_evidence(tmp_path):
    workbook_path = tmp_path / "model.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Risk"
    worksheet["A1"] = 42  # Source constants are deliberately not copied.
    worksheet["B1"] = "=EXP(A1)"
    workbook.save(workbook_path)
    _minimal_docx(tmp_path / "paper-notes.docx")
    (tmp_path / "legacy.xls").write_bytes(b"legacy-placeholder")

    manifest = build_source_manifest(tmp_path)
    assets = {item["file_name"]: item for item in manifest["assets"]}

    assert manifest["summary"]["asset_count"] == 3
    assert manifest["summary"]["xlsx_formula_cells"] == 1
    assert assets["model.xlsx"]["formulas"] == [
        {"sheet": "Risk", "cell": "B1", "expression": "=EXP(A1)"}
    ]
    assert "42" not in json.dumps(assets["model.xlsx"]["formulas"])
    assert assets["paper-notes.docx"]["table_count"] == 1
    assert assets["paper-notes.docx"]["external_targets"] == [
        "https://doi.org/10.1/test"
    ]
    assert assets["legacy.xls"]["extraction_status"] == (
        "legacy_excel_requires_lossless_conversion"
    )
    assert manifest["governance"]["clinical_execution_allowed"] is False
