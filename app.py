from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
from routers import auth, crud
from db.database import init_db
from core.shared_utilities import format_validation_errors

load_dotenv()

app = FastAPI()
init_db()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))
app.include_router(auth.router)
app.include_router(crud.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": format_validation_errors(exc.errors())
        }
    )



