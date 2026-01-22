from __future__ import annotations

import json
from typing import Any

from aio_pika import Message, DeliveryMode, connect_robust

from .settings import Settings


async def publish(settings: Settings, queue_name: str, obj: dict[str, Any]) -> None:
    conn = await connect_robust(
        host=settings.mq_host,
        port=settings.mq_port,
        login=settings.mq_user,
        password=settings.mq_password,
        virtualhost=settings.mq_vhost,
    )
    channel = await conn.channel()
    await channel.default_exchange.publish(
        Message(body=json.dumps(obj).encode("utf-8"), delivery_mode=DeliveryMode.PERSISTENT),
        routing_key=queue_name,
    )
    await conn.close()
