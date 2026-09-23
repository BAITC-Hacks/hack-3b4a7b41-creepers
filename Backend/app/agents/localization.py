"""Small deterministic RU/KZ response layer; catalog values are never translated/invented."""
import re


def detect_language(message):
    if re.search(r"[әғқңөұүһі]|\b(маған|керек|рахмет)\b", message.casefold()):
        return "kk"
    if re.search(r"\b(мне|нужен|нужно|покажи|найди|есть|добавь|сравни|отмена)\b", message.casefold()):
        return "ru"
    return None


def localize(response):
    if response.error:
        translations = {
            "product_selection_required": "Алдымен тауарды таңдаңыз немесе оның ID нөмірін көрсетіңіз.",
            "product_not_found": "Каталогтан нақты сәйкестік табылмады.",
            "insufficient_stock": "Қор жеткіліксіз немесе өзгерді. Санын азайтып, қайта тексеріңіз.",
            "pending_action_missing": "Растауды күтіп тұрған қосу әрекеті жоқ.",
            "stock_unknown": "Каталогта қор туралы расталған дерек жоқ.",
        }
        response.message = translations.get(response.error.code, "Сұрауды орындау мүмкін болмады. Қайта көріңіз.")
        response.error.message = response.message
        return response
    intent = response.intent
    if response.pending_confirmation:
        pending = response.pending_confirmation
        response.message = f"Себетке қосуды растаңыз: {pending.product.name}. Саны: {pending.quantity}. Қолда бар: {pending.available_stock}."
        pending.message = response.message
    elif intent == "product_search":
        response.message = "Каталогтан табылған тауарлар. Бірнеше нұсқа болса, қажетті тауарды таңдаңыз." if response.products else "Каталогтың тексерілген бөлігінен нақты сәйкестік табылмады. Тауар түрі мен номиналды токты нақтылаңыз."
    elif intent == "product_compare":
        response.message = "Салыстыру тек каталогтағы деректерге негізделген. Баға, қор және техникалық параметрлер кестеде берілген. Белгісіз мәндер: «Нет данных»." if len(response.products) >= 2 else "Салыстыру үшін екі тауарды таңдаңыз."
    elif intent == "add_to_cart_confirm":
        response.message = "Тауар прототиптің жергілікті себетіне қосылды. EKT сайтында тапсырыс рәсімделген жоқ."
    elif intent == "cancel_cart_action":
        response.message = "Қосу әрекеті тоқтатылды. Себет өзгерген жоқ."
    elif intent == "add_to_cart_prepare":
        response.message = "Қажетті санын көрсетіңіз, мысалы: «5 дана қос»."
    elif intent in {"product_details", "stock_check", "certificate_request", "alternative_request"} and response.products:
        p = response.products[0]
        if intent == "certificate_request":
            response.message = "Каталогтағы сертификаттар: " + "; ".join(p.certificates) if p.certificates else "Каталогта сертификат туралы расталған дерек жоқ."
        else:
            response.message = f"{p.name}. " + (f"Қолда бар: {p.stock}." if p.stock is not None else "Каталогта қор туралы расталған дерек жоқ.")
            if intent == "product_details":
                response.message += "\n" + ("; ".join(f"{k}: {v}" for k, v in p.specifications.items()) or "Каталогта сипаттамалар туралы расталған дерек жоқ.")
            if response.alternatives:
                response.message += " Баламалар төменде көрсетілген. Толық өзара алмастыру мүмкіндігін маманмен тексеріңіз."
            elif intent == "alternative_request":
                response.message += " Расталған балама табылмады."
    elif intent in {"payment_info", "delivery_info", "minimum_order"}:
        response.message = {
            "payment_info": "Жеке тұлғаларға онлайн карта, алған кезде қолма-қол немесе алып кету кезінде карта/қолма-қол төлем қолжетімді. Заңды тұлғалар шот бойынша төлей алады. Нақты тәсілді рәсімдеу кезінде тексеріңіз. Карта деректерін чатқа жібермеңіз.",
            "delivery_info": "Қазақстан бойынша жеткізу бар. Алматыда келісуден кейінгі бағдар — 48 сағат. Нақты мерзім мен құнды менеджер растайды; олар қалаға, мекенжайға, сомаға, салмақ пен көлемге байланысты. Алып кету — дайындық расталғаннан кейін.",
            "minimum_order": "Бірыңғай ең аз тапсырыс мөлшері расталған ашық шарттарда көрсетілмеген. Артикул бойынша ең аз партия мен еселікті менеджерден нақтылаңыз.",
        }[intent] + "\nДереккөз: https://ekt.kz/about/faq/"
    elif intent == "procurement_analysis":
        response.message = "Сатып алу талдауы төмендегі кестеде. Өз Excel файлыңызды жүктей аласыз. Тауарды таңдап, қосуды бөлек растаңыз." if response.products else "Excel файлын жүктеңіз: бірінші баған — тауар, екінші баған — саны. Әр қосу үшін жеке растау қажет."
    elif intent == "photo_identification":
        response.message = "Суретті жүктеңіз. Нақты тану үшін AI кілті және OpenAI арқылы өңдеуге келісім қажет. DEMO режимінде көрсетілген нұсқалар — оқу сценарийі, суретті тану нәтижесі емес."
    else:
        response.message = "Тауарды табуға, қорын, сипаттамасын және сертификатын тексеруге көмектесемін. Атауын немесе ID нөмірін көрсетіңіз."
    return response
