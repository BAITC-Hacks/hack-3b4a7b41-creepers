"""Explicit offline demonstration data. Never a fallback for EKT failures."""
from app.clients.ekt_client import matches_query
from app.core.errors import AppError
from app.schemas.product import Product, ProductSearchResponse, CatalogPage


class DemoCatalog:
    def __init__(self, checkout_base: str):
        specs = {"Номинальный ток": "25А", "Количество полюсов": "1", "Номинальное напряжение": "230В", "Характеристика срабатывания": "C"}
        self.products = {
            "900001": Product(id="900001", article="DEMO-C25", name="Автоматический выключатель C25 · 1P", category="Автоматы", description="Учебная позиция для проверки подбора и корзины. Данные синтетические.", specifications=specs, stock=24, price="2450", currency="KZT", certificates=[f"{checkout_base}/demo-certificate.html"]),
            "900002": Product(id="900002", article="DEMO-C25-ALT", name="Автоматический выключатель C25 · аналог", category="Автоматы", specifications=specs, stock=18, price="2690", currency="KZT"),
            "900003": Product(id="900003", article="DEMO-C25-ZERO", name="Автоматический выключатель C25 · нет в наличии", category="Автоматы", specifications=specs, stock=0, price="2300", currency="KZT"),
            "900004": Product(id="900004", article="DEMO-C40", name="Автоматический выключатель C40 · 1P", category="Автоматы", specifications={**specs, "Номинальный ток": "40А"}, stock=12, price="3100", currency="KZT"),
            "900005": Product(id="900005", article="DEMO-CABLE", name="Кабель ВВГнг 3×2,5", category="Кабель", specifications={"Количество жил": "3", "Сечение": "2,5 мм²"}, stock=120, price="780", currency="KZT", description="Учебная единица продажи: 1 метр."),
        }
        self.products["900001"].name = "Автомат Schneider 25А · 1P · DEMO"
        self.products["900001"].specifications = {**specs, "Торговая марка": "Schneider"}
        self.products["900002"].specifications = {**specs, "Торговая марка": "IEK"}
        self.products["900004"].name = "Автомат Schneider 40А · 1P · DEMO"
        self.products["900004"].specifications["Торговая марка"] = "Schneider"
        self.products["900005"].stock = 60
        self.products["900006"] = Product(id="900006", article="DEMO-SOCKET", name="Розетка DEMO 16А с заземлением", category="Розетки", specifications={"Номинальный ток": "16А"}, stock=45, price="1100", currency="KZT")
        for offset, (name, category, stock, price, features) in enumerate([
            ("Автомат IEK C10 · 1P", "Автоматы", 32, 1650, {**specs, "Номинальный ток": "10А", "Торговая марка": "IEK"}),
            ("Автомат Schneider C16 · 1P", "Автоматы", 21, 2500, {**specs, "Номинальный ток": "16А", "Торговая марка": "Schneider"}),
            ("Автомат ABB C32 · 1P", "Автоматы", 16, 3200, {**specs, "Номинальный ток": "32А", "Торговая марка": "ABB"}),
            ("Автомат IEK C63 · 3P", "Автоматы", 9, 6700, {**specs, "Номинальный ток": "63А", "Количество полюсов": "3", "Торговая марка": "IEK"}),
            ("Кабель NYM 3×1,5", "Кабель", 200, 520, {"Количество жил": "3", "Сечение": "1,5 мм²"}),
            ("Кабель ПВС 2×1,5", "Кабель", 85, 390, {"Количество жил": "2", "Сечение": "1,5 мм²"}),
            ("Щит распределительный на 12 модулей", "Щиты", 14, 8500, {"Модулей": "12", "Степень защиты": "IP40"}),
            ("Щит распределительный на 24 модуля", "Щиты", 6, 14800, {"Модулей": "24", "Степень защиты": "IP40"}),
            ("УЗО 40А · 30мА · 2P", "УЗО", 8, 12900, {"Номинальный ток": "40А", "Ток утечки": "30мА", "Количество полюсов": "2"}),
            ("УЗО 63А · 30мА · 2P", "УЗО", 0, 15600, {"Номинальный ток": "63А", "Ток утечки": "30мА", "Количество полюсов": "2"}),
            ("Контактор 25А · катушка 230В", "Контакторы", 11, 9400, {"Номинальный ток": "25А", "Напряжение катушки": "230В"}),
            ("Реле напряжения 63А", "Реле", 7, 18100, {"Номинальный ток": "63А", "Номинальное напряжение": "230В"}),
            ("Светильник LED 36Вт · 4000К", "Светильники", 44, 5600, {"Мощность": "36Вт", "Цветовая температура": "4000К"}),
            ("Лампа LED E27 12Вт · 4000К", "Лампы", 100, 750, {"Мощность": "12Вт", "Цоколь": "E27"}),
            ("Клемма соединительная на 3 проводника", "Клеммы", 180, 220, {"Проводников": "3"}),
            ("Кабель-канал 40×25 мм", "Кабель-каналы", 70, 680, {"Размер": "40×25 мм"}),
            ("DIN-рейка 35 мм · 1 м", "Монтажные принадлежности", 28, 950, {"Ширина": "35 мм", "Длина": "1 м"}),
            ("Выключатель одноклавишный 10А", "Выключатели", 55, 1450, {"Номинальный ток": "10А", "Клавиш": "1"}),
        ], start=7):
            identifier = str(900000 + offset)
            self.products[identifier] = Product(id=identifier, article=f"DEMO-{offset:03}", name=name, category=category, stock=stock, price=price, currency="KZT", specifications=features, description="Синтетическая учебная позиция. Не является предложением EKT.")
        for product in self.products.values():
            product.source = "demo_catalog"

    async def get_product_detail(self, product_id):
        product = self.products.get(str(product_id))
        if product is None:
            raise AppError("product_not_found", "Товар не найден в учебном каталоге.", 404)
        return product.model_copy(deep=True)

    async def search_products(self, query):
        return ProductSearchResponse(query=query, scanned_pages=1, products=[p.model_copy(deep=True) for p in self.products.values() if matches_query(p, query)])

    async def get_products(self, page=1):
        products = list(self.products.values())
        return CatalogPage(page=page, products=[p.model_copy(deep=True) for p in products[(page - 1) * 12:page * 12]], has_next=page * 12 < len(products))
