"""Domain errors raised by services. main.py maps them to HTTP responses, so services stay
free of HTTP details and are easy to unit test."""


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class AuthenticationError(AppError):
    status_code = 401


class PermissionDeniedError(AppError):
    status_code = 403
