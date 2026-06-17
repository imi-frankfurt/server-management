# limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Hier konfigurierst du deinen Limiter (z.B. auch die Redis-URL, falls genutzt)
limiter = Limiter(key_func=get_remote_address)