"""Сервис XLSX-экспорта для нормализованных товаров каталога."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Sequence, cast

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.models import CatalogProduct
from app.utils.wildberries import serialize_characteristics


class XlsxExporter:
    """Собрать XLSX-книгу из нормализованных доменных моделей."""

    HEADERS: tuple[str, ...] = (
        "Ссылка на товар",
        "Артикул",
        "Название",
        "Цена",
        "Описание",
        "Ссылки на изображения",
        "Характеристики",
        "Название селлера",
        "Ссылка на селлера",
        "Размеры товара",
        "Остатки по товару",
        "Рейтинг",
        "Количество отзывов",
    )

    def export(self, products: Sequence[CatalogProduct], query: str) -> bytes:
        """Создать XLSX-книгу в памяти и вернуть ее бинарное содержимое."""

        workbook = Workbook()
        worksheet = cast(Worksheet, workbook.active)
        worksheet.title = "Каталог"
        self._write_catalog_sheet(worksheet, products)
        self._write_meta_sheet(workbook, query=query, products_count=len(products))

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def _write_catalog_sheet(
        self,
        worksheet: Worksheet,
        products: Sequence[CatalogProduct],
    ) -> None:
        """Записать основной лист каталога со всеми запрошенными полями товара."""

        worksheet.append(self.HEADERS)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        for row_index, product in enumerate(products, start=2):
            worksheet.append(
                [
                    product.product_url,
                    product.article,
                    product.name,
                    product.price,
                    product.description,
                    ", ".join(product.image_urls),
                    serialize_characteristics(product.characteristics),
                    product.seller_name,
                    product.seller_url,
                    ", ".join(product.sizes),
                    product.stock,
                    product.rating,
                    product.reviews_count,
                ]
            )
            for cell in worksheet[row_index]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        column_widths = {
            "A": 28,
            "B": 16,
            "C": 36,
            "D": 14,
            "E": 52,
            "F": 52,
            "G": 52,
            "H": 26,
            "I": 28,
            "J": 22,
            "K": 18,
            "L": 12,
            "M": 18,
        }
        for column_name, width in column_widths.items():
            worksheet.column_dimensions[column_name].width = width

    def _write_meta_sheet(self, workbook: Workbook, query: str, products_count: int) -> None:
        """Записать вспомогательные метаданные для трассируемости сформированного отчета."""

        worksheet = cast(Worksheet, workbook.create_sheet("Метаданные"))
        worksheet.append(["Параметр", "Значение"])
        worksheet.append(["Поисковый запрос", query])
        worksheet.append(["Количество товаров", products_count])
        worksheet.append(["Дата генерации (UTC)", datetime.now(UTC).isoformat()])

        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        worksheet.column_dimensions["A"].width = 24
        worksheet.column_dimensions["B"].width = 52
