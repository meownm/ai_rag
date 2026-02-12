from app.services.connectors.registry import ConnectorRegistry, ConnectorRegistryError, registry


def register_default_connectors() -> ConnectorRegistry:
    from app.services.connectors.confluence import ConfluenceAttachmentConnector, ConfluencePagesConnector
    from app.services.connectors.file_catalog import FileCatalogConnector
    from app.services.connectors.s3_catalog import S3CatalogConnector

    registry.register(ConfluencePagesConnector())
    registry.register(ConfluenceAttachmentConnector())
    registry.register(FileCatalogConnector())
    registry.register(S3CatalogConnector())
    return registry
