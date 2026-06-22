import json
import hashlib
from fastapi import status
from core.shared_utilities import error_response
from db import models
from sqlalchemy.orm import Session


def log_ansible_output(session: Session, log_content: str):
    try:
        log_entry = models.AnsibleLogs(log_content=log_content)
        session.add(log_entry)
        session.commit()
    except Exception as e:
        error_response(f"Failed to log Ansible output: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

def ansible_export(session : Session, actor : str | None = None):
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
        
        ansible_log_content = {
            "hosts": hosts,
            "users": users_payload,
        }
        json_hash_value = json.dumps(ansible_log_content, sort_keys=True, separators=(',', ':'))
        current_hash = hashlib.sha256(json_hash_value.encode('utf-8')).hexdigest()
        content_entry = session.query(models.AnsibleContent).filter(models.AnsibleContent.content_hash == current_hash).first()

        if not content_entry:
            content_entry = models.AnsibleContent(content_hash=current_hash, json_data=json_hash_value)
            session.add(content_entry)
        
        new_query = models.AnsibleQuery(actor=actor, content=content_entry)
        session.add(new_query)
        session.commit()
        
        return ansible_log_content

    except Exception as e:
        error_response(f"Failed to fetch users: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)