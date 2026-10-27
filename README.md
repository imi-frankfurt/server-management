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

## Background jobs

### Disabled-user sync

Users that are disabled in Keycloak are synced to the local database by an in-process scheduler:
their server assignments are removed and they are deactivated locally.

- The sync runs once at startup and then every `SYNC_INTERVAL_MINUTES` minutes (default `15`, `0` disables it).
- It replaces the former external crontab job. **Remove any existing crontab entry that calls
  `/api/restricted/sync` from existing deployments.**
- The endpoint `GET /api/restricted/sync` (authenticated via the `X-API-Key` header matching `SYNC_API`)
  remains available for manual runs. It returns `409` while a sync is already in progress.
  The endpoint is rate limited to one request per 5 minutes, and a request answered with `409` also counts
  towards that limit, so retrying right after a `409` returns `429` until the 5-minute window has passed.
- The scheduler is designed for a single process. When running multiple uvicorn workers or replicas,
  set `SYNC_INTERVAL_MINUTES=0` on all but one of them (or add a cross-process guard such as
  `pg_try_advisory_lock`), otherwise every process runs its own sync.
