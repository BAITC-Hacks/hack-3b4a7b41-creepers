"""Bounded orchestration over the existing parser/catalog. No cart writes."""
import asyncio
import re
import time
from app.core.errors import AppError
from app.schemas.procurement import ProcurementReport, ProcurementRow


def summarize(report: ProcurementReport, cart=None) -> ProcurementReport:
    # Account for duplicate rows and quantities already in this session's cart.
    used = {key: item.quantity for key, item in (cart or {}).items()}
    for row in report.rows:
        if row.product:
            product = row.product
            if product.stock is None:
                row.available, row.missing, row.status = None, None, "unknown"
            else:
                remaining = max(0, int(product.stock) - used.get(product.id, 0))
                row.available = min(row.requested, remaining)
                row.missing = row.requested - row.available
                row.status = "available" if not row.missing else "shortage"
                used[product.id] = used.get(product.id, 0) + row.available
    report.positions = len(report.rows)
    report.requested = sum(row.requested for row in report.rows)
    report.available = sum(row.available or 0 for row in report.rows)
    report.missing = sum(row.missing or 0 for row in report.rows)
    report.complete_positions = sum(row.status == "available" for row in report.rows)
    report.shortage_positions = sum(row.status == "shortage" for row in report.rows)
    report.unresolved_positions = sum(row.status not in {"available", "shortage"} for row in report.rows)
    return report


class ProcurementService:
    def __init__(self, products, alternatives, *, demo=False):
        self.products, self.alternatives = products, alternatives
        self.source = "demo_catalog" if demo else "ekt_catalog"
        self.context = {}

    def save(self, session_id, *, report=None, photos=None):
        now = time.monotonic()
        self.context = {key: value for key, value in self.context.items() if now - value[0] < 3600}
        if session_id not in self.context and len(self.context) >= 1000:
            self.context.pop(next(iter(self.context)))
        old = self.context.get(session_id, (now, None, []))
        self.context[session_id] = (now, report if report is not None else old[1], photos if photos is not None else old[2])

    def stored(self, session_id):
        value = self.context.get(session_id)
        return value if value and time.monotonic() - value[0] < 3600 else (0, None, [])

    async def analyze(self, text: str, cart=None) -> ProcurementReport:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line or re.search(r"(?i)(наименование|название|тауар).*(количество|кол-во|саны)", line):
                continue
            cells = [cell.strip() for cell in re.split(r"[|\t;]", line)]
            match = re.fullmatch(r"(.+?)\s+(\d+)\s*(?:шт\.?|штук|дана|м)?", line) if len(cells) == 1 else None
            if match:
                cells = [match[1], match[2]]
            query = cells[0][:200]
            quantity = re.fullmatch(r"(\d{1,7})(?:\s*(?:шт\.?|штук|дана|м))?", cells[1]) if len(cells) >= 2 else None
            valid = bool(quantity and 0 < int(quantity[1]) <= 1000000 and query)
            rows.append(ProcurementRow(query=query, requested=int(quantity[1]) if valid else 0,
                status="unknown" if valid else "invalid", note="" if valid else "Нужны название и целое количество: Товар | 10."))
        report = ProcurementReport(rows=rows[:8], truncated=len(rows) > 8, source=self.source)
        semaphore = asyncio.Semaphore(3)

        async def resolve(row):
            if row.status == "invalid":
                return
            async with semaphore:
                try:
                    async with asyncio.timeout(8):
                        result = await self.products.search(row.query)
                        row.candidates = result.products[:5]
                        row.note = "Поиск по части каталога." if result.partial else ""
                        if not row.candidates:
                            row.status, row.note = "not_found", "Точное совпадение не найдено в просмотренном каталоге."
                        elif len(row.candidates) > 1:
                            row.status = "selection_required"
                            row.note += " Выберите нужный товар из кандидатов."
                        else:
                            row.product = row.candidates[0]
                            if row.product.stock is not None and row.product.stock < row.requested:
                                row.alternatives = (await self.alternatives.find(row.product)).alternatives
                except (AppError, TimeoutError):
                    row.status, row.note = "error", "Не удалось проверить каталог. Повторите анализ."
        await asyncio.gather(*(resolve(row) for row in report.rows))
        return summarize(report, cart)

    async def select(self, report, row_index, product_id, cart):
        if not 0 <= row_index < len(report.rows):
            raise AppError("invalid_row", "Строка закупки не найдена.", 404)
        row = report.rows[row_index]
        allowed = {p.id for p in row.candidates} | {a.product.id for a in row.alternatives}
        if product_id not in allowed:
            raise AppError("invalid_candidate", "Выберите товар из предложенных вариантов.", 422)
        row.product = await self.products.detail(product_id)
        row.alternatives = []
        if row.product.stock is not None and row.product.stock < row.requested:
            row.alternatives = (await self.alternatives.find(row.product)).alternatives
        return summarize(report, cart)
