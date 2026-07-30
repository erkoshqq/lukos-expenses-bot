from __future__ import annotations


class ServiceError(Exception):
    """Базовая ошибка сервисного слоя, текст показывается пользователю как есть."""


class PermissionDeniedError(ServiceError):
    def __init__(self, message: str = "Недостаточно прав для этого действия.") -> None:
        super().__init__(message)


class NotFoundError(ServiceError):
    def __init__(self, message: str = "Объект не найден.") -> None:
        super().__init__(message)
