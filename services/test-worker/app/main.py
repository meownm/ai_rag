from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Callable, Awaitable

from aio_pika import IncomingMessage, connect_robust
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .job_contract import validate_job
from .logger import JsonLogger
from .metrics import jobs_total, job_duration_seconds
from .mq import publish
from .settings import load_settings, Settings


JobHandler = Callable[[dict[str, Any]], Awaitable[None]]


async def handle_test_job(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


REGISTRY: dict[str, JobHandler] = {
    "test-job": handle_test_job,
}


class WorkerState:
    def __init__(self) -> None:
        self.ready: bool = False


async def _declare_queues(ch, cfg: Settings) -> tuple[str, str, str]:
    main = cfg.worker_queue_name
    retry = main + cfg.worker_retry_suffix
    dlq = main + cfg.worker_dlq_suffix

    await ch.declare_queue(main, durable=True)
    await ch.declare_queue(dlq, durable=True)
    await ch.declare_queue(
        retry,
        durable=True,
        arguments={
            "x-message-ttl": cfg.worker_retry_delay_ms,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": main,
        },
    )
    return main, retry, dlq


async def _process_message(cfg: Settings, logger: JsonLogger, state: WorkerState, msg: IncomingMessage) -> None:
    # We ack manually; do not requeue forever.
    raw = msg.body.decode("utf-8", errors="replace")

    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("message must be JSON object")
        job = validate_job(obj)
    except Exception as exc:
        jobs_total.labels(app=cfg.app_name, job_type="unknown", result="invalid").inc()
        logger.exception("invalid job message", exc=exc, plane="control", event="job_invalid")
        await msg.ack()
        return

    request_id = str(job.correlation.get("request_id", "")) if job.correlation else ""
    logger.info(
        "job received",
        plane="data",
        event="job_received",
        job_id=job.job_id,
        job_type=job.type,
        request_id=(request_id or None),
        attempt=job.attempt,
    )

    if job.type not in REGISTRY:
        dlq = cfg.worker_queue_name + cfg.worker_dlq_suffix
        await publish(cfg, dlq, obj)
        jobs_total.labels(app=cfg.app_name, job_type=job.type, result="unknown_type").inc()
        logger.error(
            "unknown job_type, sent to dlq",
            plane="control",
            event="job_invalid",
            job_id=job.job_id,
            job_type=job.type,
            dlq=dlq,
        )
        await msg.ack()
        return

    handler = REGISTRY[job.type]

    try:
        with job_duration_seconds.labels(app=cfg.app_name, job_type=job.type).time():
            await asyncio.wait_for(handler(job.payload), timeout=cfg.worker_handler_timeout_seconds)

        jobs_total.labels(app=cfg.app_name, job_type=job.type, result="ok").inc()
        logger.info(
            "job processed",
            plane="data",
            event="job_ok",
            job_id=job.job_id,
            job_type=job.type,
            request_id=(request_id or None),
            attempt=job.attempt,
        )
        await msg.ack()
        return
    except Exception as exc:
        if job.attempt < cfg.worker_max_attempts:
            retry_q = cfg.worker_queue_name + cfg.worker_retry_suffix
            new_obj = dict(obj)
            new_obj["attempt"] = int(job.attempt) + 1
            await publish(cfg, retry_q, new_obj)

            jobs_total.labels(app=cfg.app_name, job_type=job.type, result="retry").inc()
            logger.exception(
                "job failed, retry published",
                exc=exc,
                plane="control",
                event="job_fail",
                job_id=job.job_id,
                job_type=job.type,
                attempt=job.attempt,
                next_attempt=int(job.attempt) + 1,
                retry_queue=retry_q,
            )
            await msg.ack()
            return
        else:
            dlq = cfg.worker_queue_name + cfg.worker_dlq_suffix
            await publish(cfg, dlq, obj)

            jobs_total.labels(app=cfg.app_name, job_type=job.type, result="dlq").inc()
            logger.exception(
                "job failed, sent to dlq (max_attempts exceeded)",
                exc=exc,
                plane="control",
                event="job_fail",
                job_id=job.job_id,
                job_type=job.type,
                attempt=job.attempt,
                dlq=dlq,
            )
            await msg.ack()
            return


async def _worker_loop(cfg: Settings, logger: JsonLogger, state: WorkerState) -> None:
    conn = await connect_robust(
        host=cfg.mq_host,
        port=cfg.mq_port,
        login=cfg.mq_user,
        password=cfg.mq_password,
        virtualhost=cfg.mq_vhost,
    )
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=cfg.worker_prefetch)

    main, _, _ = await _declare_queues(ch, cfg)
    q = await ch.declare_queue(main, durable=True)

    logger.info("worker started", plane="control", event="worker_started", queue=main)
    state.ready = True

    sem = asyncio.Semaphore(cfg.worker_concurrency)

    async def on_message(msg: IncomingMessage) -> None:
        async with sem:
            await _process_message(cfg, logger, state, msg)

    await q.consume(on_message, no_ack=False)

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        state.ready = False
        await conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_settings()
    logger = JsonLogger(app=cfg.app_name, env=cfg.app_env, level=cfg.log_level)
    state = WorkerState()
    app.state.cfg = cfg
    app.state.logger = logger
    app.state.worker_state = state

    logger.info("startup", plane="control", event="startup", app_port=cfg.app_port)

    task = asyncio.create_task(_worker_loop(cfg, logger, state))
    try:
        yield
    finally:
        task.cancel()
        logger.info("shutdown", plane="control", event="shutdown")


app = FastAPI(title="test-worker", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    st: WorkerState = app.state.worker_state
    return {"status": "ok" if st.ready else "not_ready"}


@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
