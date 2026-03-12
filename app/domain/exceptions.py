"""Исключения приложения, используемые между слоями."""


class WildberriesClientError(RuntimeError):
    """Выбрасывается, когда публичные эндпоинты Wildberries не возвращают корректный payload."""


class CatalogNotFoundError(RuntimeError):
    """Выбрасывается, когда поисковый запрос не возвращает товаров."""
