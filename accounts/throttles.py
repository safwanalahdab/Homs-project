from rest_framework.throttling import SimpleRateThrottle

class LoginIPThrottle(SimpleRateThrottle):
    scope = "login_ip"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)  # IP
        if not ident:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginIdentifierThrottle(SimpleRateThrottle):
    scope = "login_identifier"

    def get_cache_key(self, request, view):
        identifier = (request.data.get("identifier") or "").strip().lower()
        if not identifier:
            return None
        return self.cache_format % {"scope": self.scope, "ident": identifier}