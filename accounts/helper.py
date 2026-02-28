from django.conf import settings

REFRESH_COOKIE_NAME = "refresh_token"

def set_refresh_cookie(response, refresh_token: str):
    """
    Attach the JWT refresh token to the response as an HttpOnly cookie.

    Security rationale:
    - HttpOnly: prevents JavaScript access (mitigates token theft via XSS).
    - Secure: ensures the cookie is sent only over HTTPS (recommended for production).
    - SameSite:
        * "None" is required for cross-site scenarios (frontend and backend on different domains),
          BUT it must be paired with Secure=True in modern browsers.
        * "Lax" is usually suitable for local development when using same-site/proxy setups.

    Cookie scope:
    - path="/api/auth/" limits the cookie to auth endpoints (refresh/logout), reducing exposure.

    Note:
    - max_age should ideally match your refresh token lifetime. 
    """
    # تأكد من أن secure مفعّل إذا كنت في بيئة الإنتاج
    secure = not settings.DEBUG

    # إعداد SameSite بناءً على بيئة الإنتاج أو التطوير
    samesite = "Lax" if settings.DEBUG else "None"

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,  # مهم لضمان أن الكوكيز تكون غير قابلة للوصول عبر JavaScript
        secure= True,  # فقط في بيئة الإنتاج يجب أن يكون true
        samesite="None",  # تحديد قيمة SameSite للكوكيز
        path="/api/auth/",  # تحديد المسار الذي يمكن الوصول فيه للكوكيز
        max_age=14 * 24 * 60 * 60,  # صلاحية الكوكيز لمدة 14 يوم
    )



def clear_refresh_cookie(response):
    """
    Remove the refresh token cookie from the client.

    Must match the same 'path' used in set_refresh_cookie, otherwise the cookie may not be removed.
    """
    # لحذف الكوكيز
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth/",  # نفس المسار الذي تم تحديده عند تعيين الكوكيز
    )

"""
### Refresh Token Cookie Helpers

These helpers manage storing the JWT refresh token in an HttpOnly cookie.

- **set_refresh_cookie(response, refresh_token)**:
  Stores the refresh token in a cookie named `refresh_token` with:
  - `HttpOnly` enabled to prevent JavaScript access (XSS mitigation).
  - `Secure` enabled in production so the cookie is only sent over HTTPS.
  - `SameSite=None` in production to support cross-domain frontend/backends (requires HTTPS).
  - `path=/api/auth/` to restrict the cookie to authentication endpoints only.
  - `max_age=14 days` as the cookie lifetime.

- **clear_refresh_cookie(response)**:
  Deletes the same cookie using the same cookie path to ensure proper removal.
"""
