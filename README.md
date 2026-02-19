# IMI Server Manager

The IMI Server Manager is a specialized tool designed to manage metadata and configuration details for servers. It serves as a modern replacement for the legacy system, which relied on unstructured Keycloak attributes.

The primary goal is to store server information in a relational database (PostgreSQL) to ensure data atomicity, consistency, and efficient retrieval via both a graphical user interface (GUI) and a RESTful API.

## Table of Contents

- [Target Audience](#target-audience)
- [Functional Requirements](#functional-requirements)
- [Technology Stack](#technology-stack)

## Target Audience

The system supports two distinct user groups:

### A. System Administrators (GUI Users)

- **Goal:** Manual infrastructure management
- **Tasks:** Create servers, update IP addresses, and manage access rights via a web frontend
- **Authentication:** Single Sign-On (SSO) via Keycloak

### B. DevOps & Automation Services (API Users)

- **Goal:** Automated configuration retrieval
- **Tasks:** Query endpoints to determine user redirects (e.g., "Which server IP is for User X?")
- **Authentication:** Secure token-based API access

## Functional Requirements

The application centers around the "Server" entity and supports the following features:

- **Server Management:** Users can add/remove servers (identified by a unique ID)
- **Alias Assignment:** Assign multiple aliases to a single server
- **Access Control (Ignored Users):** Assign multiple ignored users to a server
- **Redirect Logic:** If a user is marked as "ignored" on Server A, the system redirects them to their correct server
- **Synchronization:** Automatically or manually fetch the users from the Keycloak via Keycloak Admin API

## Technology Stack

- **Language:** Python 3.14.2
- **Framework:** FastAPI - High-performance framework for the web application and REST API
- **Database:** PostgreSQL - Relational database for structured server metadata
- **Container:** Docker - Consistent deployment of application and database
- **Authentication:** Keycloak - Handles OIDC authentication and role management