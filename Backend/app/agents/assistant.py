from app.agents.intent import classify
from app.agents.tools import AssistantTools
from app.core.errors import AppError
from app.schemas.chat import ChatResponse


class Assistant:
    def __init__(self, tools: AssistantTools):
        self.tools = tools

    async def reply(self, session_id: str, message: str) -> ChatResponse:
        decision = classify(message)
        try:
            async with self.tools.sessions.use(session_id) as session:
                if decision.intent == "cancel_cart_action":
                    self.tools.cart.cancel(session)
                    return ChatResponse(intent=decision.intent, message="Ожидающее добавление отменено.", cart=self.tools.cart.view(session))
                if decision.intent == "add_to_cart_confirm":
                    cart = await self.tools.cart.confirm(session)
                    return ChatResponse(intent=decision.intent, message="Товар добавлен в локальную демонстрационную корзину.", cart=cart, checkout_url=cart.checkout_url)
                if decision.intent == "add_to_cart_prepare":
                    if decision.quantity is None:
                        return ChatResponse(intent=decision.intent, message="Укажите количество, например «добавь 5 штук».")
                    product_id = self.tools.sessions.selected(session, decision.product_id)
                    pending = await self.tools.cart.prepare(session, product_id, decision.quantity)
                    self.tools.sessions.remember(session, [pending.product])
                    return ChatResponse(intent=decision.intent, message=pending.message, products=[pending.product],
                                        pending_confirmation=pending, cart=self.tools.cart.view(session))
                if decision.intent in {"payment_info", "delivery_info", "minimum_order"}:
                    return ChatResponse(intent=decision.intent, message=self.tools.conditions.answer(decision.intent))
                if decision.intent == "product_search":
                    if not decision.query:
                        return ChatResponse(intent=decision.intent, message="Укажите название или артикул товара.")
                    result = await self.tools.search(session, decision.query)
                    text = "Найденные товары:" if result.products else "Товары не найдены в просмотренной части каталога."
                    if len(result.products) > 1:
                        text += " Выберите товар по ID, например «товар 515291»."
                    if result.partial:
                        text += " Поиск ограничен частью каталога."
                    return ChatResponse(intent=decision.intent, message=text, products=result.products)
                if decision.intent in {"product_details", "stock_check", "certificate_request", "alternative_request"}:
                    product = await self.tools.detail(session, decision.product_id)
                    alternatives = []
                    partial = False
                    if decision.intent == "alternative_request" or product.stock == 0:
                        result = await self.tools.alternatives.find(product)
                        alternatives, partial = result.alternatives, result.partial
                    if decision.intent == "stock_check":
                        text = ("Остаток недоступен в текущем источнике." if product.stock is None else
                                "Товар отсутствует в наличии." if product.stock == 0 else f"Остаток: {product.stock}.")
                    elif decision.intent == "certificate_request":
                        text = ("Сертификаты из каталога: " + "; ".join(product.certificates) if product.certificates
                                else "Сертификат не найден в доступных данных каталога.")
                    elif decision.intent == "alternative_request":
                        text = "Возможные альтернативы:" if alternatives else "Подтверждённые альтернативы не найдены."
                    else:
                        text = f"{product.name}. "
                        text += ("; ".join(f"{key}: {value}" for key, value in product.specifications.items())
                                 if product.specifications else "Характеристики недоступны в текущем источнике.")
                        text += (f" Цена: {product.price}" + (f" {product.currency}." if product.currency else " (валюта не указана).")
                                 if product.price is not None else " Цена недоступна в текущем источнике.")
                    if product.stock == 0 and decision.intent != "stock_check":
                        text += " Товар отсутствует в наличии."
                    if alternatives:
                        text += " Взаимозаменяемость требует проверки."
                    if partial:
                        text += " Проверена только часть возможных альтернатив."
                    if product.data_warnings:
                        text += " " + " ".join(product.data_warnings)
                    return ChatResponse(intent=decision.intent, message=text, products=[product], alternatives=alternatives)
                return ChatResponse(intent=decision.intent, message="Могу найти товар, проверить наличие, характеристики и сертификаты. Укажите название или ID.")
        except AppError as exc:
            return ChatResponse(intent=decision.intent, message=exc.message, error=exc.info())
