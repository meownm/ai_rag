from __future__ import annotations

from prometheus_client import Counter, Histogram

jobs_total = Counter("jobs_total", "Total jobs processed by workers", ["app", "job_type", "result"])
job_duration_seconds = Histogram("job_duration_seconds", "Job processing duration (seconds)", ["app", "job_type"])
