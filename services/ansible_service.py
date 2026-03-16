from fastapi import status
from core.shared_utilities import error_response
from db import models
from sqlalchemy.orm import Session

def ansible_export(session : Session):
    try:
        users = session.query(models.User).order_by(models.User.id.asc()).all()
        servers = session.query(models.Server).order_by(models.Server.id.asc()).all()

        hosts = []
        users_payload = []

        for server in servers:
            aliases = session.query(models.Alias).filter(models.Alias.server_id == server.id).order_by(models.Alias.id.asc()).all()
            ignored_entries = session.query(models.IgnoredUser).filter(
                models.IgnoredUser.server_id == server.id
            ).order_by(models.IgnoredUser.id.asc()).all()

            alias_values = [item.alias for item in aliases if item.alias]
            ignored_users = sorted([item.username for item in ignored_entries if item.username])
            authorized_users = sorted([u.username for u in server.users if u.username])

            hosts.append({
                "hostname": server.ip,
                "alias": alias_values[0] if alias_values else (server.name or ""),
                "ignored_users": ignored_users,
                "authorized_users": authorized_users,
            })

        for user in users:
            public_keys = sorted([pk.key_content for pk in user.public_keys if pk.key_content])
            users_payload.append({
                "user_id": user.username,
                "public_keys": public_keys,
            })

        return {
            "hosts": hosts,
            "users": users_payload,
        }

    except Exception as e:
        error_response(f"Failed to fetch users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)