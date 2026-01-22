from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from aio_pika import Message, DeliveryMode, connect_robust


def make_job_message(job_type: str, payload: dict[str, Any], attempt: int = 0) -> dict[str, Any]:
    return {
        "job_id": str(uuid.uuid4()),
        "type": job_type,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
        "attempt": attempt,
    }


async def publish_job(queue_name: str, job: dict[str, Any]) -> None:
    host = os.getenv("MQ_HOST", "localhost")
    port = int(os.getenv("MQ_PORT", "54040"))
    user = os.getenv("MQ_USER", "rag_mq")
    password = os.getenv("MQ_PASSWORD", "rag_mq_pass")
    vhost = os.getenv("MQ_VHOST", "/")

    conn = await connect_robust(host=host, port=port, login=user, password=password, virtualhost=vhost)
    channel = await conn.channel()
    await channel.default_exchange.publish(
        Message(body=json.dumps(job).encode("utf-8"), delivery_mode=DeliveryMode.PERSISTENT),
        routing_key=queue_name,
    )
    await conn.close()


async def _run(queue: str, job_type: str, attempt: int) -> None:
    job = make_job_message(job_type=job_type, payload={"hello": "world"}, attempt=attempt)
    await publish_job(queue_name=queue, job=job)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--attempt", type=int, default=0)
    args = p.parse_args()

    asyncio.run(_run(queue=args.queue, job_type=args.type, attempt=args.attempt))
    print("Published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
