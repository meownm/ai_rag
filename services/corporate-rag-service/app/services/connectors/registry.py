from __future__ import annotations

from app.services.connectors.base import SourceConnector


class ConnectorRegistryError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector) -> None:
        self._connectors[connector.source_type] = connector

    def get(self, source_type: str) -> SourceConnector:
        connector = self._connectors.get(source_type)
        if connector is None:
            raise ConnectorRegistryError("I-CONNECTOR-UNKNOWN-SOURCE", f"Unknown source_type: {source_type}")
        configured, reason = connector.is_configured()
        if not configured:
            raise ConnectorRegistryError(
                "I-CONNECTOR-NOT-CONFIGURED",
                reason or f"Connector {source_type} is not configured",
            )
        return connector

    def list_registered(self) -> list[str]:
        return sorted(self._connectors.keys())


registry = ConnectorRegistry()
