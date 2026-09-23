class ConditionsService:
    """Replace only with verified partner policy data, never generated rules."""

    def answer(self, intent: str) -> str:
        subject = {
            "payment_info": "условиям оплаты",
            "delivery_info": "условиям доставки",
            "minimum_order": "минимальному заказу",
        }[intent]
        return f"Информация по {subject} недоступна в текущем источнике."
