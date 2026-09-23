"""Deterministic Russian/English phrase rules. No state or side effects."""
import re
from dataclasses import dataclass
from typing import Literal

Intent = Literal[
    "product_search", "product_details", "stock_check", "certificate_request",
    "alternative_request", "payment_info", "delivery_info", "minimum_order",
    "add_to_cart_prepare", "add_to_cart_confirm", "cancel_cart_action", "unknown",
]


@dataclass(frozen=True)
class Decision:
    intent: Intent
    query: str | None = None
    product_id: str | None = None
    quantity: int | None = None


CONFIRMATIONS = {
    "да", "да добавь", "да подтверждаю", "подтверждаю", "подтверждаю добавление",
    "да подтверждаю добавление", "yes", "yes add", "confirm", "i confirm",
}
CANCELLATIONS = {"нет", "отмена", "отмени", "отмени добавление", "не добавляй", "cancel", "no"}


def classify(message: str) -> Decision:
    text = message.casefold().strip().replace("ё", "е")
    normalized = re.sub(r"[.,!]+", " ", text)
    normalized = " ".join(normalized.split())
    # Question marks and extra clauses are deliberately not discarded.
    if normalized in CONFIRMATIONS:
        return Decision("add_to_cart_confirm")
    if normalized in CANCELLATIONS:
        return Decision("cancel_cart_action")
    identifier = re.search(r"(?:\bid\s*[:#]?|\bтовар(?:а|у)?\s*[:#]?)\s*([\w.-]*\d[\w.-]*)", text)
    product_id = identifier.group(1).rstrip(".") if identifier else None
    if re.fullmatch(r"\d{1,20}", text):
        return Decision("product_details", product_id=text)
    if re.search(r"добав|в корзин|\badd\b", text):
        quantity = re.search(r"(?<![\w.,])(-?\d+(?:[.,]\d+)?)\s*(?:шт\b|штук|единиц|pieces?\b)", text)
        if not quantity:
            quantity = re.search(r"(?:добавь|добавить|добавьте|add)\s+(-?\d+(?:[.,]\d+)?)(?![\w.,])", text)
        value = None
        if quantity:
            token = quantity.group(1)
            value = int(token) if re.fullmatch(r"-?\d{1,9}", token) else 0
        return Decision("add_to_cart_prepare", product_id=product_id, quantity=value)
    patterns: list[tuple[Intent, str]] = [
        ("minimum_order", r"минимальн|минимум|minimum order"),
        ("payment_info", r"оплат|платеж|рассроч|payment|pay\b"),
        ("delivery_info", r"достав|самовывоз|delivery|shipping"),
        ("alternative_request", r"аналог|альтернатив|замен|alternative"),
        ("certificate_request", r"сертификат|certificate"),
        ("stock_check", r"налич|остат|склад|stock|availab"),
        ("product_details", r"характерист|спецификац|подробн|цен[аыуе]|стоимост|specification|details|price"),
    ]
    for intent, pattern in patterns:
        if re.search(pattern, text):
            return Decision(intent, product_id=product_id)
    if product_id:
        return Decision("product_details", product_id=product_id)
    if re.search(r"найди|найти|ищу|нуж[еен]|покажи|поиск|автомат|кабел|выключател|\bsearch\b|\bfind\b|\d", text):
        query = re.sub(r"\b(?:мне|нужен|нужна|нужно|нужны|найди|найти|ищу|покажи|пожалуйста|на|артикул[уа]?|по|search|find)\b", " ", text)
        query = re.sub(r"\s+", " ", query).strip(" .,!?:")
        return Decision("product_search", query=query or None)
    return Decision("unknown")
