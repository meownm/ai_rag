import logging
from pythonjsonlogger import jsonlogger


class _StructuredContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "stage"):
            record.stage = None
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_StructuredContextFilter())
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(stage)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
