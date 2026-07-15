from rest_framework.serializers import Serializer


class InvalidFormError(Exception):
    CODE = 400
    TYPE = "InvalidFormError"

    def __init__(self, serializer: Serializer):
        self.serializer = serializer
        super().__init__(serializer)

    def __str__(self, *args, **kwargs):
        return "Invalid form"

    def get_errors(self) -> dict:
        errors = {}
        for field, message in self.serializer.errors.items():
            errors[field] = message

        return errors


class AuthorAlreadyExistsError(Exception):
    CODE = 400
    TYPE = "AuthorAlreadyExistsError"

    def __str__(self, *args, **kwargs):
        return "Author already exists"


class AuthorNotFoundError(Exception):
    CODE = 400
    TYPE = "AuthorNotFoundError"

    def __str__(self, *args, **kwargs):
        return "Author not found"


class InvalidPasswordError(Exception):
    CODE = 401
    TYPE = "InvalidPasswordError"

    def __str__(self, *args, **kwargs):
        return "Invalid password"


class InvalidJWTTokenError(Exception):
    CODE = 401
    TYPE = "InvalidJWTTokenError"

    def __str__(self, *args, **kwargs):
        return "Invalid JWT token"


class RefreshTokenNotFoundError(Exception):
    CODE = 400
    TYPE = "RefreshTokenNotFoundError"

    def __str__(self, *args, **kwargs):
        return "Refresh token not found"


class RefreshTokenExpiredError(Exception):
    CODE = 401
    TYPE = "RefreshTokenExpiredError"

    def __str__(self, *args, **kwargs):
        return "Refresh token expired"


class AuthorCodeNotFoundError(Exception):
    CODE = 400
    TYPE = "AuthorCodeNotFoundError"

    def __str__(self, *args, **kwargs):
        return "Author code not found"


class AuthorIsBlockedError(Exception):
    CODE = 403
    TYPE = "AuthorIsBlockedError"

    def __str__(self, *args, **kwargs):
        return "Author is blocked"


class MinimumLengthPasswordError(Exception):
    CODE = 400
    TYPE = "MinimumLengthPasswordError"

    def __str__(self, *args, **kwargs):
        return "Password is too short"


class CommonPasswordError(Exception):
    CODE = 400
    TYPE = "CommonPasswordError"

    def __str__(self, *args, **kwargs):
        return "Password is too common"


class NumericPasswordError(Exception):
    CODE = 400
    TYPE = "NumericPasswordError"

    def __str__(self, *args, **kwargs):
        return "Password is entirely numeric"


class AuthorImpersonationError(Exception):
    CODE = 403
    TYPE = "AuthorImpersonationError"

    def __str__(self, *args, **kwargs):
        return "No permission to impersonate"


class OrganizationAlreadyExistsError(Exception):
    CODE = 400
    TYPE = "OrganizationAlreadyExistsError"

    def __str__(self, *args, **kwargs):
        return "Organization already exists"


class OrganizationINNAlreadyExistsError(Exception):
    CODE = 400
    TYPE = "OrganizationINNAlreadyExistsError"

    def __str__(self, *args, **kwargs):
        return "Organization with this INN already exists"


class OFDDataRequestError(Exception):
    CODE = 400
    TYPE = "OFDDataRequestError"

    def __str__(self, *args, **kwargs):
        return "Error requesting OFD data"


class PaymentUnavailableError(Exception):
    CODE = 400
    TYPE = "PaymentUnavailableError"

    def __str__(self, *args, **kwargs):
        return "Payment is temporarily unavailable"


class InvoiceNotFoundError(Exception):
    CODE = 400
    TYPE = "InvoiceNotFoundError"

    def __str__(self, *args, **kwargs):
        return "Invoice not found"


class OrganizationNotFoundError(Exception):
    CODE = 400
    TYPE = "OrganizationNotFoundError"

    def __str__(self, *args, **kwargs):
        return "Organization not found"


class AccessDeniedError(Exception):
    CODE = 403
    TYPE = "AccessDeniedError"

    def __str__(self, *args, **kwargs):
        return "Access denied"
