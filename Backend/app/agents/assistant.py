import asyncio
import re
from app.agents.intent import classify
from app.agents.localization import detect_language, localize
from app.agents.tools import AssistantTools
from app.core.errors import AppError
from app.schemas.chat import ChatResponse


class Assistant:
    def __init__(self, tools: AssistantTools, language=None):
        self.tools = tools
        self.language = language

    async def reply(self, session_id: str, message: str) -> ChatResponse:
        try:
            async with self.tools.sessions.use(session_id) as session:
                photo_context = self.tools.procurement.stored(session_id)[2]
                if session.last_product is None and len(photo_context) == 1 and not session.recent_products:
                    self.tools.sessions.remember(session, photo_context)
                session.language = detect_language(message) or session.language
                language = session.language
            result = await self._reply(session_id, message)
            return localize(result) if language == "kk" else result
        except AppError as exc:
            return ChatResponse(message=exc.message, error=exc.info())

    async def _reply(self, session_id: str, message: str) -> ChatResponse:
        decision = classify(message)
        try:
            async with self.tools.sessions.use(session_id) as session:
                if self.language and decision.intent == "unknown":
                    decision = await self.language.understand(message, decision, {
                        "last_query": session.last_query,
                        "selected_product_id": session.last_product.id if session.last_product else None,
                        "recent_product_ids": [p.id for p in session.recent_products[:5]],
                    })
                if decision.intent == "product_compare":
                    identifiers = re.findall(r"(?<![\w])\d{5,12}(?![\w])", message)
                    identifiers = list(dict.fromkeys(identifiers or [p.id for p in session.recent_products]))[:2]
                    if len(identifiers) < 2:
                        return ChatResponse(intent=decision.intent, message="Выберите два товара кнопкой «Сравнить» или укажите два ID.")
                    products = list(await asyncio.gather(*(self.tools.products.detail(key) for key in identifiers)))
                    keys = set(products[0].specifications) | set(products[1].specifications)
                    differences = [key for key in sorted(keys) if products[0].specifications.get(key) != products[1].specifications.get(key)]
                    if products[0].price != products[1].price or products[0].currency != products[1].currency:
                        differences.append("цена / валюта")
                    if products[0].stock != products[1].stock:
                        differences.append("наличие")
                    text = "Основные различия: " + ", ".join(differences) if differences else "В доступных параметрах различий не найдено."
                    return ChatResponse(intent=decision.intent, message=text + ". Отсутствующие значения не означают равенство; полная взаимозаменяемость не подтверждена.", products=products)
                if decision.intent == "procurement_analysis":
                    session.procurement = self.tools.procurement.stored(session_id)[1] or session.procurement
                    if session.procurement is None and self.tools.cart.demo:
                        session.procurement = await self.tools.procurement.analyze("Автомат Schneider 25А | 10\nРозетка DEMO | 30\nКабель ВВГ | 100", session.cart)
                        self.tools.procurement.save(session_id, report=session.procurement)
                    report = session.procurement
                    if report is None:
                        return ChatResponse(intent=decision.intent, message="Загрузите Excel: первая колонка — название, вторая — количество. Покажу наличие, дефицит и кандидатов. Ничего не добавляю автоматически.")
                    return ChatResponse(intent=decision.intent, message=f"Анализ закупки: {report.complete_positions} полностью доступных позиций, {report.shortage_positions} с недостаточным остатком, {report.unresolved_positions} требуют уточнения. " + ("DEMO MODE: учебная закупка." if self.tools.cart.demo else "Источник: каталог EKT."), products=[r.product for r in report.rows if r.product])
                if decision.intent == "photo_identification":
                    session.photo_candidates = self.tools.procurement.stored(session_id)[2] or session.photo_candidates
                    if self.tools.cart.demo and not session.photo_candidates:
                        session.photo_candidates = (await self.tools.products.search("Schneider 25А")).products
                    if session.photo_candidates:
                        self.tools.sessions.remember(session, session.photo_candidates)
                    if not self.tools.cart.demo and (not self.language or not self.language.settings.openai_api_key.get_secret_value()):
                        return ChatResponse(intent=decision.intent, message="Реальное распознавание фото требует AI-ключа на сервере. Сейчас можно ввести маркировку вручную или переключиться в DEMO MODE: там доступен явно обозначенный учебный сценарий.", products=session.photo_candidates)
                    return ChatResponse(intent=decision.intent, message=("Demo Mode: распознавание изображения работает на демонстрационном сценарии. Эти учебные кандидаты не получены анализом вашего фото." if self.tools.cart.demo else "Загрузите фото маркировки и включите распознавание через OpenAI. Покажу предположение и кандидатов каталога; параметры нужно проверить."), products=session.photo_candidates)
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
                    query = decision.query
                    if re.fullmatch(r"(?:schneider(?: electric)?|шнайдер|iek|legrand|abb)", query, re.I):
                        session.last_query = query
                        self.tools.sessions.remember(session, [])
                        return ChatResponse(intent=decision.intent, message="Какой номинальный ток и тип товара нужны? Например: «25А автомат».")
                    rating = re.fullmatch(r"\d+(?:[.,]\d+)?\s*[aа]", query, re.I)
                    if rating and session.last_query:
                        previous = re.sub(r"\b\d+(?:[.,]\d+)?\s*[aа]\b", "", session.last_query, flags=re.I)
                        query = f"{previous.strip()} {query}"
                    session.last_query = query
                    result = await self.tools.search(session, query)
                    text = "Найденные товары:" if result.products else "Я не нашёл точного совпадения в каталоге EKT. Поиск выполнен по доступной части каталога."
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
                        session.recent_products = [product, *(item.product for item in alternatives)]
                    if partial:
                        text += " Проверена только часть возможных альтернатив."
                    if product.data_warnings:
                        text += " " + " ".join(product.data_warnings)
                    return ChatResponse(intent=decision.intent, message=text, products=[product], alternatives=alternatives)
                return ChatResponse(intent=decision.intent, message="Могу найти товар, проверить наличие, характеристики и сертификаты. Укажите название или ID.")
        except AppError as exc:
            return ChatResponse(intent=decision.intent, message=exc.message, error=exc.info())
