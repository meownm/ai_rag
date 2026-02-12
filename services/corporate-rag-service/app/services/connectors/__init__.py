from app.services.connectors.file_catalog import FileCatalogConnector
from app.services.connectors.registry import ConnectorRegistry, ConnectorRegistryError, registry
from app.services.connectors.stubs import ConfluenceAttachmentConnector, ConfluenceConnector, S3CatalogConnector


def register_default_connectors() -> ConnectorRegistry:
    registry.register(ConfluenceConnector())
    registry.register(ConfluenceAttachmentConnector())
    registry.register(FileCatalogConnector())
    registry.register(S3CatalogConnector())
    return registry
