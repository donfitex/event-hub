import hashlib
from django.core.cache import cache
from django.contrib.auth import authenticate
from rest_framework.throttling import BaseThrottle


def login_attempt(request, email, password):
    ip = BaseThrottle().get_ident(request)
    key = "login:" + hashlib.sha256(f"{email.lower()}:{ip}".encode()).hexdigest()
    if cache.get(key, 0) >= 5:
        return None, "Too many failed login attempts. Try again in 15 minutes."
    user = authenticate(request, email=email.lower(), password=password)
    if user:
        cache.delete(key)
        return user, None
    cache.add(key, 0, 900)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, 900)
    return None, "Invalid email or password."
