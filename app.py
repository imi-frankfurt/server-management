from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
from routers import auth, server, user, blacklist, activity_log
from db.database import init_db
from core.shared_utilities import format_validation_errors
load_dotenv()

# Load custom OpenAPI spec from api.json
def load_openapi_spec():
    try:
        api_json_path = os.path.join(os.path.dirname(__file__), "docs", "api.json")
        with open(api_json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading api.json: {e}")
        return {}

app = FastAPI(docs_url="/docs", redoc_url=None, openapi_url="/openapi.json")

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
    "*"
]

FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,  # Exact origins, not wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(server.router)
app.include_router(user.router)
app.include_router(blacklist.router)
app.include_router(activity_log.router)


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

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"\n{'='*60}")
    print(f"UNHANDLED EXCEPTION: {type(exc).__name__}")
    print(f"Message: {str(exc)}")
    print(f"Path: {request.url.path}")
    print(f"{'='*60}")
    traceback.print_exc()
    print(f"{'='*60}\n")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__
        }
    )



