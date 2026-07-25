# Free Demo Deployment

## Recommended portfolio setup

Use [Render](https://render.com/docs/free) for the Django API and React static site, plus [Neon PostgreSQL](https://neon.com/pricing) for the database. `render.yaml` defines both services. This is appropriate for a small, synthetic-data portfolio demo because it deploys automatically from GitHub and keeps the frontend/backend separate.

It is not an acceptable real clinical deployment: Render free services can sleep and have an ephemeral filesystem, and Neon Free does not provide the compliance/contractual controls required for PHI.

## Deployment steps

1. Create a new Neon PostgreSQL project and copy its pooled PostgreSQL connection string.
2. Push this repository to GitHub after completing `docs/PUBLISHING_CHECKLIST.md`.
3. In Render, select **New → Blueprint** and choose the repository. Render reads `render.yaml`.
4. Create the API service first. Set these secret/environment values:

   ```text
   DATABASE_URL=<Neon PostgreSQL URL, including sslmode=require>
   PUBLIC_BASE_URL=https://<api-service>.onrender.com
   ALLOWED_HOSTS=<api-service>.onrender.com
   CSRF_TRUSTED_ORIGINS=https://<api-service>.onrender.com,https://<web-service>.onrender.com
   CORS_ALLOWED_ORIGINS=https://<web-service>.onrender.com
   ```

   Render generates `SECRET_KEY`; do not replace it with a development key. The API build runs migrations and collects static files.
5. After the API URL is known, configure the static frontend service with:

   ```text
   REACT_APP_API_URL=https://<api-service>.onrender.com
   ```

   Trigger a frontend redeploy. Create React App embeds this value at build time.
6. Open the API health endpoint at `https://<api-service>.onrender.com/api/health-check/`, then exercise registration/login and a basic API request with synthetic data.

## Free-tier trade-offs

| Service | What it provides | Important limit |
| --- | --- | --- |
| Render free web service | HTTPS, GitHub deployment, public demo URL | Sleeps after inactivity; local files are lost on restart; no durable worker/disk. |
| Neon Free | Hosted PostgreSQL for a low-traffic demo | Limited compute/storage; no HIPAA/compliance scope for this use. |
| [GitHub Free](https://github.com/pricing) | Repository, Issues, Actions CI | Public repositories expose every committed file and history. |

If the user-facing UI is commercial, do not substitute [Vercel Hobby](https://vercel.com/docs/plans/hobby): its free plan is restricted to personal/non-commercial use. Render is the simpler single-provider demo option here.

## Production path

For an actual healthcare deployment, move to a paid provider and obtain appropriate data-processing/compliance agreements, encrypted backups, audit monitoring, incident response, MFA/least privilege, durable object storage, a managed worker/cache, and a penetration/security review. Do not treat passing FHIR tests or this demo configuration as certification.
