from fastapi import HTTPException, status
import re

def check_duplicate(session, model, **kwargs):
    return session.query(model).filter_by(**kwargs).first() is not None

def record_exists(session, model, **kwargs) -> bool:
    return session.query(model).filter_by(**kwargs).first() is not None


def success_response(data=None, message: str = "Success", status_code: int = 200):
    # Return data directly without wrapper
    if data is not None:
        return data
    return {"message": message}


def error_response(message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail=message
    )


def format_validation_errors(errors):
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "type": error["type"],
            "message": error["msg"]
        })
    return formatted_errors

def validate_ip_address(ip_address: str) -> bool:
    ipv4_pattern = "^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    return bool(re.match(ipv4_pattern, ip_address))

def validate_keycloak(keycloak_id: str) -> bool:
    # Keycloak GUID
    keycloak_pattern = "^(?:\\{{0,1}(?:[0-9a-fA-F]){8}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){12}\\}{0,1})$"
    return bool(re.match(keycloak_pattern, keycloak_id))

def check_local_id(id: str) -> bool:
    local_id_pattern = r"^\d+$"
    if bool(re.match(local_id_pattern, id)):
        return True  # It's a local DB ID
    return False
