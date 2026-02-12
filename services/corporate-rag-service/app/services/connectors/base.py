from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceDescriptor:
    source_type: str
    external_ref: str
    title: str
    last_modified: datetime | None = None
    checksum_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceItem:
    source_type: str
    external_ref: str
    title: str
    markdown: str
    url: str = ""
    author: str | None = None
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncContext:
    max_items_per_run: int
    page_size: int
    incremental_enabled: bool


@dataclass(frozen=True)
class ConnectorError:
    error_code: str
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class ConnectorFetchResult:
    item: SourceItem | None = None
    error: ConnectorError | None = None


class SourceConnector(Protocol):
    source_type: str

    def is_configured(self) -> tuple[bool, str | None]:
        ...

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        ...

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        ...
