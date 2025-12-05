import os
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from .models import TelegramSubscription


@csrf_exempt
def telegram_webhook(request):
    """
    Простейший webhook: обрабатываем /start <username>
    и сохраняем chat_id -> user.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")
    try:
        data = request.json() if hasattr(request, "json") else None
        if data is None:
            import json
            data = json.loads(request.body.decode("utf-8"))
        message = data.get("message") or {}
        chat_id = str(message.get("chat", {}).get("id"))
        text = (message.get("text") or "").strip()
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    if not chat_id or not text:
        return HttpResponseBadRequest("Missing chat_id or text")

    if text.startswith("/start"):
        parts = text.split()
        if len(parts) >= 2:
            username = parts[1]
            User = get_user_model()
            user = User.objects.filter(username=username).first()
            if user:
                TelegramSubscription.objects.update_or_create(
                    chat_id=chat_id, defaults={"user": user, "is_active": True}
                )
                send_message(chat_id, "Привязка выполнена. Вы будете получать оповещения.")
            else:
                send_message(chat_id, "Пользователь не найден. Укажите свой username после /start")
        else:
            send_message(chat_id, "Отправьте /start <username> для привязки аккаунта.")
    else:
        send_message(chat_id, "Команда не распознана. Используйте /start <username>.")
    return JsonResponse({"ok": True})


def send_message(chat_id: str, text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except Exception:
        pass
