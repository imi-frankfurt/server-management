# IMI Server Manager

Internal tool for UKG Institut für Medizininformatik Frankfurt admins.
It centralizes server metadata, user-to-server assignments, and exceptions in one place.
The UI and automation use the same data to keep routing and access decisions consistent.

## Features in use

- **Server registry:** Store server name and IP.
- **Aliases:** Multiple aliases per server.
- **Ignored users (Ignore List):** Define users that should not be touched by the configuration management on specific servers to prevent accidental deactivation of external accounts.
- **User assignments:** Assign users to servers, including a primary server.
- **User sync:** Sync users and public keys from Keycloak.
- **Activity log:** Track changes (create, update, delete, sync).
- **Ansible export:** Export servers, aliases, ignored users, and authorized users.

## Tech stack

- **API:** FastAPI (Python)
- **Database:** PostgreSQL
- **Auth/SSO:** Keycloak
- **Deployment:** Docker

## Dependencies

- `requirements.txt` contains only the runtime dependencies that go into the Docker image.
- `requirements-dev.txt` adds development tools (`pur`, `pip-check`): `pip install -r requirements-dev.txt`.
- The image is built from `python:3.13-slim` in two stages and runs as the non-root user `app`
  (uid `10001`). The local `docker-compose.yml` runs the container as root so the mounted mkcert key stays readable.

## Background jobs

### User sync

The local user database is synced with Keycloak by an in-process scheduler (the same full sync as
`POST /api/user/sync`):

- New Keycloak users are added with their public keys, and users removed from Keycloak are deleted locally.
- Public keys of existing users are added/removed to match the `pubkey` attribute in Keycloak.
- Users disabled in Keycloak have their server assignments removed and are deactivated locally;
  users re-enabled in Keycloak are reactivated.
- Scheduled runs are recorded in the activity log with the actor `scheduler`, but only if users were
  added, updated or deleted. Runs without changes are not logged, so the "last synced" timestamp
  (`GET /api/activity/status`) only moves when the scheduled sync actually changed something or a manual sync ran.

- The sync runs once at startup and then every `SYNC_INTERVAL_MINUTES` minutes (default `15`, `0` disables it).
- It replaces the former external crontab job. **Remove any existing crontab entry that calls
  `/api/restricted/sync` from existing deployments.**
- `POST /api/user/sync` (admin role) remains available for manual full syncs. It returns `409` while a sync
  is already in progress.
- The endpoint `GET /api/restricted/sync` (authenticated via the `X-API-Key` header matching `SYNC_API`)
  remains available for manual runs of the disabled-user part only. It returns `409` while a sync is already in progress.
  The endpoint is rate limited to one request per 5 minutes, and a request answered with `409` also counts
  towards that limit, so retrying right after a `409` returns `429` until the 5-minute window has passed.
- The scheduler is designed for a single process. When running multiple uvicorn workers or replicas,
  set `SYNC_INTERVAL_MINUTES=0` on all but one of them (or add a cross-process guard such as
  `pg_try_advisory_lock`), otherwise every process runs its own sync.
