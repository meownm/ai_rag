from __future__ import annotations

import argparse
import asyncio

from publish_test_job import make_job_message, publish_job


async def _run(queue: str, job_type: str, count: int) -> None:
    for _ in range(count):
        job = make_job_message(job_type=job_type, payload={"hello": "world"})
        await publish_job(queue_name=queue, job=job)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--count", type=int, required=True)
    args = p.parse_args()

    asyncio.run(_run(queue=args.queue, job_type=args.type, count=args.count))
    print("Published batch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
