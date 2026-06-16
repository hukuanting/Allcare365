import React, { useEffect } from "react";
import FHIR from "fhirclient";

export default function Launch() {
  useEffect(() => {
    FHIR.oauth2.authorize({
      "clientId": "my_web_app",
      "scope": "launch patient/*.read openid fhirUser",
      "redirectUri": "http://localhost:3000/dashboard",
      "iss": "http://localhost:8000/fhir" // Pointing to our Django FHIR server
    });
  }, []);

  return (
    <div className="launch-screen">
      <h1>Connecting to Allcare 365 FHIR System...</h1>
      <p>Please wait while we authorize your access.</p>
    </div>
  );
}
