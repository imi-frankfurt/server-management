# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.1] - 2026-11-11

### Changed
- Updated Python dependencies to their latest compatible versions, including FastAPI 0.162.4, uvicorn 0.54.0, pydantic 2.14.3, sentry-sdk 2.74.0, requests 2.34.2 and psycopg2 2.9.13. SQLAlchemy stays on the 2.0 series (2.0.57).
- Updated GitHub Actions to their current major versions (Node 24 runtime): `actions/checkout@v7`, `docker/setup-buildx-action@v4`, `docker/login-action@v4`, `docker/metadata-action@v6`, `docker/setup-qemu-action@v4`, `docker/build-push-action@v7`.

## [2.3.0] - 2026-11-05

### Security
- Login now uses PKCE (S256), so the Keycloak client can require it. The verifier is kept in a short-lived `HttpOnly` cookie (`pkce_verifier`) between starting the login and exchanging the code.

### Changed
- `POST /auth/exchange-code` now responds with `400` if the `pkce_verifier` cookie is missing or expired. Frontends must call `GET /auth/login-url` with credentials so the browser stores the cookie.

## [2.2.1] - 2026-10-29

### Fixed
- Ansible export JSON no longer contains deactivated users or users without SSH keys ([#26](https://github.com/imi-frankfurt/server-management/issues/26)).

## [2.2.0] - 2026-10-28

### Security
- Docker image is now built in two stages from `python:3.13-slim` instead of the full `python:3.13` image.
- `pip`, `setuptools` and `wheel` are removed from the runtime image.
- Container runs as a non-root user (root only for local docker-compose).
- Updated vulnerable dependencies; dev tools moved to `requirements-dev.txt`.

## [2.1.0] - 2026-10-28

### Added
- In-process scheduler that keeps users in sync automatically, replacing the external crontab sync ([#20](https://github.com/imi-frankfurt/server-management/issues/20)).
- Docker images are built for pull requests and deleted when the PR is closed ([#23](https://github.com/imi-frankfurt/server-management/issues/23)).

### Fixed
- Harbor image cleanup.

## [2.0.1-rc1] - 2026-07-13

### Fixed
- Already disabled users that are still assigned to servers now get unassigned ([#19](https://github.com/imi-frankfurt/server-management/issues/19)).

## [2.0.0] - 2026-07-06

### Added
- `GET /user/disabled` to list disabled users, and syncing disabled users by unassigning them from their servers.
- `enabled` flag on `/user` and `/user/{id}` responses.
- `GET /restricted/sync` endpoint protected by an API key.
- Rate limiting on selected endpoints via slowapi.
- Improved logging for the Ansible export with timestamps (requires a DB migration).
- `GET /ansible/history` to retrieve the Ansible export history.
- Refresh token is set as a response cookie with a 30-day expiration.

### Changed
- Improved API responses and general code cleanup.
- Ansible log entries no longer store an actor (always the system).
- API documentation updated for the new endpoints and the ignored-users feature.

### Removed
- CSRF token endpoint.

## [1.0.3] - 2026-05-27

### Changed
- **Breaking:** "blacklist" renamed to "ignore list", including related endpoints and functionality.
- Docker images are now published to the IMI Harbor registry; image build workflow can be triggered manually.
- PostgreSQL image updated to version 18 in docker-compose.

### Added
- GNU AGPL v3 license.

## [1.0.2] - 2026-05-18

### Fixed
- User unassignment logging handles a missing `primary_user` attribute.
- Python app image pinned to a specific version from the GitHub Container Registry.

## [1.0.1] - 2026-05-18

Initial release of the IMI Server Manager.

### Added
- Keycloak-based authentication with JWT validation, direct login, token verification and refresh tokens.
- Server management (CRUD) with IP address validation, restricted to admins.
- User management: sync from Keycloak (including removal of users no longer in Keycloak), listing, details, updates.
- User-server assignment and unassignment by local ID or Keycloak UUID, with a primary-user flag.
- Blacklist for users excluded from management.
- Activity logging with actor information and a filterable logs endpoint.
- Ansible export API.
- Security headers middleware and CORS configuration.
- Docker and Docker Compose setups for production and local Keycloak, including PostgreSQL, plus `.env.example`.
- GitHub Actions workflow to build and push Docker images.
- README and API specification.

[2.3.1]: https://github.com/imi-frankfurt/server-management/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/imi-frankfurt/server-management/compare/v2.2.1...v2.3.0
[2.2.1]: https://github.com/imi-frankfurt/server-management/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/imi-frankfurt/server-management/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/imi-frankfurt/server-management/compare/v2.0.1-rc1...v2.1.0
[2.0.1-rc1]: https://github.com/imi-frankfurt/server-management/compare/v2.0.0...v2.0.1-rc1
[2.0.0]: https://github.com/imi-frankfurt/server-management/compare/v1.0.3...v2.0.0
[1.0.3]: https://github.com/imi-frankfurt/server-management/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/imi-frankfurt/server-management/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/imi-frankfurt/server-management/releases/tag/v1.0.1
