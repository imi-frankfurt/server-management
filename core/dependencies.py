from fastapi import Depends, HTTPException
from typing import List, Dict
from services.authentication_service import verify_token

def get_token_data(token_data: Dict = Depends(verify_token)) -> Dict:
    """
    Dependency to get and verify the bearer token.
    Returns the complete token data including user info and roles.
    """
    return token_data

def get_current_user(token_data: Dict = Depends(get_token_data)) -> Dict:
    """
    Extract user information from the verified token.
    """
    return token_data["user_info"]

def get_user_roles(token_data: Dict = Depends(get_token_data)) -> List[str]:
    """
    Extract user roles from the verified token.
    """
    return token_data["roles"]

def require_role(required_role: str):
    """
    Dependency factory: Check if the user has a specific role.
    """
    def role_checker(token_data: Dict = Depends(get_token_data)):
        roles = token_data["roles"]
        if required_role not in roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied: Role '{required_role}' required"
            )
        return roles
    return role_checker