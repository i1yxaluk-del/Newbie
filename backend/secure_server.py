"""Рабочая точка входа API: согласие, CAPTCHA и очередь доставки в MongoDB.

Импорт server сначала создаёт приложение и читает .env, затем этот модуль
добавляет проверку тела запроса и заменяет функции проверки CAPTCHA/доставки.
Это тот же объект app, а не второй API. Запускать с одним worker: отправитель
внутри процесса не имеет межпроцессной блокировки. Подробнее: docs/development/CODE_READING.md.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from starlette.responses import JSONResponse

import server

logger = logging.getLogger("mspshield.production")
app = server.app


class RequireExplicitConsentMiddleware:
    """Требовать JSON-объект с consent=true перед обычной проверкой модели.

    ASGI receive отдаёт тело частями и только один раз. После чтения возвращаем
    сохранённые байты FastAPI через replay_receive, иначе обработчик не увидит их.
    """

    def __init__(self, app):
        """Сохранить следующий обработчик цепочки ASGI, не создавать новое приложение."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Проверить только POST /api/leads; остальные запросы передать без изменений."""
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/leads":
            await self.app(scope, receive, send)
            return

        chunks = []
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)
        try:
            payload = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if not isinstance(payload, dict) or payload.get("consent") is not True:
            response = JSONResponse(
                {"detail": "consent_required"}, status_code=400
            )
            await response(scope, receive, send)
            return

        sent = False

        async def replay_receive():
            """Один раз вернуть сохранённое тело последующему обработчику."""
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


app.add_middleware(RequireExplicitConsentMiddleware)


async def verify_smartcaptcha_strict(token: str | None, client_ip: str) -> bool:
    """При настроенном ключе отклонить запрос без подтверждения CAPTCHA.

    Пустой ключ означает выключенную интеграцию. Сбой провайдера по умолчанию
    не пропускает запрос; явный FAIL_OPEN меняет эту политику и требует решения.
    """
    if not server.SMARTCAPTCHA_SERVER_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                server.SMARTCAPTCHA_VERIFY_URL,
                params={
                    "secret": server.SMARTCAPTCHA_SERVER_KEY,
                    "token": token,
                    "ip": client_ip,
                },
            )
        return response.json().get("status") == "ok"
    except Exception as exc:  # noqa: BLE001
        fail_open = os.environ.get("SMARTCAPTCHA_FAIL_OPEN", "false").lower() == "true"
        logger.error("SmartCaptcha verification unavailable; fail_open=%s; error=%s", fail_open, type(exc).__name__)
        return fail_open


server.verify_smartcaptcha = verify_smartcaptcha_strict


def _enabled_channels() -> list[str]:
    """Снять список настроенных получателей на момент постановки заявки в очередь."""
    channels = []
    if server.telegram.is_enabled():
        channels.append("telegram")
    if server.email_integration.is_enabled():
        channels.append("email")
    if server.webhook.is_enabled():
        channels.append("webhook")
    if server.max_integration.is_alert_channel():
        channels.append("max")
    if server.kaiten.is_enabled():
        channels.append("kaiten")
    return channels


async def _send_channel(channel: str, lead: Dict[str, Any]) -> bool:
    """Отправить в один канал; True — подтверждённый успех адаптера, не чтение человеком."""
    if channel == "telegram":
        return await server.telegram.send(lead)
    if channel == "email":
        return await server.email_integration.send(lead)
    if channel == "webhook":
        code = await server.webhook.send(lead)
        return bool(code and 200 <= code < 300)
    if channel == "max":
        return await server.max_integration.send(lead)
    if channel == "kaiten":
        card = await server.kaiten.create_card(lead)
        if not card or not card.get("id"):
            return False
        await server.db.leads.update_one(
            {"id": lead["id"]},
            {"$set": {"kaiten_card_id": card["id"]}},
        )
        return True
    return False


async def _process_delivery(lead_id: str) -> None:
    """Повторить оставшиеся каналы заявки; успешные убрать, ошибки назначить на потом.

    pending — ещё не подтверждённые получатели. next_retry_at хранит время UTC.
    Отказ одного канала не мешает другим. После аварии возможна повторная отправка
    между внешним успехом и его записью в Mongo: это не гарантия «ровно один раз».
    """
    job = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if not job:
        return
    pending = list(job.get("pending") or [])
    failures: Dict[str, str] = {}
    for channel in pending:
        try:
            if await _send_channel(channel, job["payload"]):
                await server.db.crm_outbox.update_one(
                    {"lead_id": lead_id}, {"$pull": {"pending": channel}}
                )
                server.inc_crm(channel, "ok")
            else:
                failures[channel] = "delivery returned false"
                server.inc_crm(channel, "error")
        except Exception as exc:  # noqa: BLE001
            failures[channel] = type(exc).__name__
            server.inc_crm(channel, "error")

    current = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if current and not current.get("pending"):
        await server.db.crm_outbox.delete_one({"lead_id": lead_id})
        return
    attempts = int((current or job).get("attempts", 0)) + 1
    # Увеличиваем паузу 60, 120, 240... секунд, максимум час: не атакуем сбойный API.
    delay = min(3600, 30 * (2 ** min(attempts, 7)))
    await server.db.crm_outbox.update_one(
        {"lead_id": lead_id},
        {"$set": {
            "attempts": attempts,
            "last_errors": failures,
            "next_retry_at": datetime.now(timezone.utc) + timedelta(seconds=delay),
            "updated_at": datetime.now(timezone.utc),
        }},
    )


async def durable_deliver_to_crm(lead: Dict[str, Any]) -> None:
    """Записать задание до отметки delivery_enqueued; саму отправку выполняет poller.

    Маркер в leads позволяет подобрать заявку после аварии до создания задания.
    Если каналы выключены, заявка остаётся в базе, но автоматической отправки при
    их позднем включении не будет: требуется отдельное операторское решение.
    """
    stored = await server.db.leads.find_one({"id": lead["id"]}, {"delivery_enqueued": 1})
    if stored and stored.get("delivery_enqueued"):
        return
    channels = _enabled_channels()
    if not channels:
        await server.db.leads.update_one({"id": lead["id"]}, {"$set": {"delivery_enqueued": True}})
        return
    now = datetime.now(timezone.utc)
    await server.db.crm_outbox.update_one(
        {"lead_id": lead["id"]},
        {"$setOnInsert": {
            "lead_id": lead["id"],
            "payload": lead,
            "pending": channels,
            "attempts": 0,
            "created_at": now,
            "next_retry_at": now,
        }},
        upsert=True,
    )
    await server.db.leads.update_one({"id": lead["id"]}, {"$set": {"delivery_enqueued": True}})
    # Единственный poller владеет отправкой: background request не конкурирует с ним.


server.deliver_to_crm = durable_deliver_to_crm


async def _outbox_worker() -> None:
    """Каждые 30 секунд подобрать новые/просроченные задания, до 20 за проход.

    Старые записи без явного delivery_enqueued=False не подбираются: нельзя
    массово повторно отправлять исторические заявки без согласованной миграции.
    """
    while True:
        now = datetime.now(timezone.utc)
        try:
            # Восстановить очередь для лида, если процесс умер после insert, до enqueue.
            cursor = server.db.leads.find({"delivery_enqueued": False}, {"_id": 0}).limit(20)
            async for lead in cursor:
                await durable_deliver_to_crm(lead)
            cursor = server.db.crm_outbox.find(
                {"next_retry_at": {"$lte": now}}, {"lead_id": 1}
            ).limit(20)
            async for job in cursor:
                await _process_delivery(job["lead_id"])
        except Exception as exc:  # worker должен переживать временную недоступность БД.
            logger.error("Outbox poll failed: %s", type(exc).__name__)
        await asyncio.sleep(30)


@app.on_event("startup")
async def _start_outbox_worker() -> None:
    """Создать индексы поиска и единственный фоновый цикл при запуске API."""
    await server.db.crm_outbox.create_index("lead_id", unique=True)
    await server.db.crm_outbox.create_index("next_retry_at")
    await server.db.leads.create_index("delivery_enqueued")
    app.state.outbox_task = asyncio.create_task(_outbox_worker())


@app.on_event("shutdown")
async def _stop_outbox_worker() -> None:
    """Запросить остановку фонового цикла; задания остаются в Mongo для нового процесса."""
    task = getattr(app.state, "outbox_task", None)
    if task:
        task.cancel()
