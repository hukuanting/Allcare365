import React, { useEffect } from "react";
import FHIR from "fhirclient";
import API_CONFIG from "../config/api";

export default function Launch() {
  useEffect(() => {
    FHIR.oauth2.authorize({
      "clientId": "my_web_app",
      "scope": "launch patient/*.read openid fhirUser",
      "redirectUri": `${window.location.origin}/dashboard`,
      "iss": `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FHIR_BASE}`,
    });
  }, []);

  return (
    <div className="launch-screen">
      <h1>Connecting to Allcare 365 FHIR System...</h1>
      <p>Please wait while we authorize your access.</p>
    </div>
  );
}
