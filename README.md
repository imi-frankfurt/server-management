# IMI Server Manager

Internal tool for UKG Institut für Medizininformatik Frankfurt admins.
It centralizes server metadata, user-to-server assignments, and exceptions in one place.
The UI and automation use the same data to keep routing and access decisions consistent.

## Features in use

- **Server registry:** Store server name and IP.
- **Aliases:** Multiple aliases per server.
- **Ignored users (blacklist):** Users that should not land on a specific server.
- **User assignments:** Assign users to servers, including a primary server.
- **User sync:** Sync users and public keys from Keycloak.
- **Activity log:** Track changes (create, update, delete, sync).
- **Ansible export:** Export servers, aliases, ignored users, and authorized users.

## Tech stack

- **API:** FastAPI (Python)
- **Database:** PostgreSQL
- **Auth/SSO:** Keycloak
- **Deployment:** Docker
