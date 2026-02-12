from fastapi import Request, HTTPException
from typing import List

def get_current_user(request: Request):
    """Prüft ob der Benutzer eingeloggt ist"""
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    return user

def get_user_roles(request: Request) -> List[str]:
    """Gibt alle Rollen des Benutzers zurück"""
    roles = request.session.get('roles', [])
    return roles

def require_role(required_role: str):
    """Dependency Factory: Prüft ob Benutzer eine bestimmte Rolle hat"""
    def role_checker(request: Request):
        roles = request.session.get('roles', [])
        if required_role not in roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Zugriff verweigert: Rolle '{required_role}' erforderlich"
            )
        return roles
    return role_checker