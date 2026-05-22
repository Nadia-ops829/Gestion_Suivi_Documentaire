from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session authentication class that bypasses CSRF checks.
    Useful when working with an external React frontend that struggles to send X-CSRFToken.
    """
    def enforce_csrf(self, request):
        # Do not perform the csrf check previously happening
        return
