from fastapi import HTTPException, status

def check_duplicate(session, model, **kwargs):
    return session.query(model).filter_by(**kwargs).first() is not None

def record_exists(session, model, **kwargs) -> bool:
    """
    Check if a record exists in the given model with the specified filter criteria.
    Usage: record_exists(session, User, id=5)
    """
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