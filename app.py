from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
from routers import auth, crud
from db.database import init_db

load_dotenv()

app = FastAPI()
init_db()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))
app.include_router(auth.router)
app.include_router(crud.router)



