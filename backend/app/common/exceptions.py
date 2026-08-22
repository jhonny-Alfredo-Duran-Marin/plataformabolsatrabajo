class AppException(Exception):
    """Excepción base de negocio. Se traduce a una respuesta HTTP por el handler global."""

    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ResourceNotFoundException(AppException):
    status_code = 404


class BusinessException(AppException):
    status_code = 422


class ForbiddenException(AppException):
    status_code = 403


class UnauthorizedException(AppException):
    status_code = 401


class ConflictException(AppException):
    status_code = 409
