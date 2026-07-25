# Public GitHub Publishing Checklist

Complete this before committing or pushing a public portfolio version.

- [ ] Confirm every patient, provider, document, screenshot, CSV, and database file is synthetic or has written publication permission.
- [ ] Check Git history as well as the working tree for `.env`, private keys, access tokens, database dumps, and tunnel logs.
- [ ] Do not stage ignored files manually (`.env`, `media/`, `*.sqlite3`, clinical uploads, Cloudflare tunnel files).
- [ ] Review untracked paths individually. Do not use `git add -A` blindly when raw source data or generated evidence may be present.
- [ ] Run `python manage.py check`, `pytest`, and the frontend test/build commands.
- [ ] Confirm all public claims: this project demonstrates FHIR/SMART/ONC-oriented work; it must not be described as certified unless formal certification exists.
- [ ] Choose a license only after confirming ownership of all code and source materials.
- [ ] Verify GitHub repository visibility and the destination remote before `git push`.
- [ ] For the public demo, use a new empty database and only synthetic accounts/data.

Suggested public commit sequence:

```bash
git status
git add README.md .env.example render.yaml medical_system/settings_production.py docs .github frontend/src
git add -u
git diff --cached --check
git commit -m "Prepare deployable Allcare 365 demo and handoff documentation"
git push origin main
```

The explicit `git add` is intentional: review any other untracked source material separately before adding it.
