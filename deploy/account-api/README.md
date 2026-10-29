# OpenDoremi account API — Aliyun deployment
Backend code: kevin.cheng's server (FastAPI) deployed to /opt/opendoremi-api/server, venv /opt/opendoremi-api/venv, user `opendoremi`.
- setup.sh: installs PostgreSQL 16 (127.0.0.1, shared_buffers 32MB, max_connections 20, work_mem 2MB), creates db/user with random password, citext, Ed25519 key (/etc/opendoremi/ed25519.pem, 400), env /etc/opendoremi-api.env (600), alembic, systemd, backup cron. Secrets are generated on the server only.
- opendoremi-api.service: uvicorn 1 worker on 127.0.0.1:8090, Restart=always, MemoryMax=200M.
- patch_nginx.py / nginx.sh: adds `location = /api/v1/catalog.json` (static) + `location /api/v1/` proxy + `/.well-known/jwks.json` to the openduolaimi HTTPS server (expects nginx-api.snippet beside it; see patch_nginx.py).
- odapi-backup.sh + opendoremi-backup.cron: daily 04:00 pg_dump gz into /var/backups/opendoremi, 14 days, local only.
- openapi-account.yaml: final spec (1.0.0-draft.2).
