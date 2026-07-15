from django.http import JsonResponse


class ExceptionHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        code = getattr(exception, "CODE", None)
        type = getattr(exception, "TYPE", None)
        if code is None or type is None:
            return None

        error = {
            "message": str(exception),
            "type": type,
            "code": code,
        }

        get_errors = getattr(exception, "get_errors", None)
        if callable(get_errors):
            error["form_errors"] = get_errors()

        return JsonResponse({"error": error}, status=code)
