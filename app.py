from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
import json
from routers import auth, crud
from db.database import init_db
from core.shared_utilities import format_validation_errors

load_dotenv()

# Load custom OpenAPI spec from api.json
def load_openapi_spec():
    try:
        # Get the absolute path to api.json
        api_json_path = os.path.join(os.path.dirname(__file__), "docs", "api.json")
        with open(api_json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading api.json: {e}")
        return {}

app = FastAPI(docs_url="/docs", redoc_url=None, openapi_url="/openapi.json")

# Override the openapi() method to use custom api.json
def custom_openapi():
    if not app.openapi_schema:
        app.openapi_schema = load_openapi_spec()
    return app.openapi_schema

app.openapi = custom_openapi

init_db()

origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:8080",
    "*"  # Allow all for development/testing
]

# Add CORS middleware BEFORE SessionMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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



