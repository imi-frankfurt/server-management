from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import logging
from routers import ansible, auth, ignorelist, server, user, activity_log, restricted
from db.database import init_db
from core.scheduler import start_scheduler, shutdown_scheduler
from core.shared_utilities import format_validation_errors
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.limiter import limiter
from routers import auth

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Load custom OpenAPI spec from api.json
def load_openapi_spec():
    try:
        api_json_path = os.path.join(os.path.dirname(__file__), "docs", "api.json")
        with open(api_json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading api.json: {e}")
        return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(docs_url="/docs", redoc_url=None, openapi_url="/openapi.json", lifespan=lifespan)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def custom_openapi():
    if not app.openapi_schema:
        app.openapi_schema = load_openapi_spec()
    return app.openapi_schema



app.openapi = custom_openapi

origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:8080"
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


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)

    csp_policy = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "form-action 'self'; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css.map http://localhost:8080 https://localhost:8080 http://127.0.0.1:8080 https://127.0.0.1:8080;"
    )

    response.headers["Content-Security-Policy"] = csp_policy
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response

app.include_router(auth.router)
app.include_router(server.router)
app.include_router(user.router)
app.include_router(ignorelist.router)
app.include_router(activity_log.router)
app.include_router(ansible.router)
app.include_router(restricted.router)



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
            "message": "Internal server error"
        }
    )



