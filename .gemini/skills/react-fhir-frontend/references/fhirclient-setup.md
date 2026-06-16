# fhirclient (SMART on FHIR) Setup

## 1. Client Initialization
Use this pattern in `frontend/src/config/fhir.js`.

```javascript
import FHIR from 'fhirclient';

export const getFHIRClient = () => {
    return FHIR.oauth2.ready();
};

export const launchSMART = (clientId, scope) => {
    FHIR.oauth2.authorize({
        clientId: clientId,
        scope: scope,
        redirectUri: './'
    });
};
```

## 2. Resource Fetching Hook
Standard React hook for loading FHIR data.

```javascript
import { useState, useEffect } from 'react';
import { getFHIRClient } from '../config/fhir';

export const useFHIRResource = (resourceType, query = {}) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getFHIRClient().then(client => {
            client.request(`${resourceType}?${new URLSearchParams(query)}`)
                .then(res => {
                    setData(res);
                    setLoading(false);
                });
        });
    }, [resourceType, JSON.stringify(query)]);

    return { data, loading };
};
```
