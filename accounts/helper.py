from django.conf import settings

REFRESH_COOKIE_NAME = "refresh_token"

def set_refresh_cookie(response, refresh_token: str):
    secure = not settings.DEBUG

    samesite = "Lax" if settings.DEBUG else "None"

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api/auth/",
        max_age=14 * 24 * 60 * 60, 
    )

def clear_refresh_cookie(response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth/",
    )