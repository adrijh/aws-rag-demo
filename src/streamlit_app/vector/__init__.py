from langchain_core.embeddings import Embeddings

from streamlit_app.config import CloudProvider, Config
from streamlit_app.config.providers import AWSConfig, AzureConfig


def build_provider_vector_store(
    cfg: Config,
    embeddings: Embeddings
):
    if cfg.cloud_provider == CloudProvider.AWS:
        from streamlit_app.vector.opensearch import build_opensearch_store

        if not isinstance(cfg.provider_cfg, AWSConfig):
            raise TypeError(f"Expected AWSConfig for AWS provider, got {type(cfg.provider_cfg).__name__}")

        return build_opensearch_store(
            cfg=cfg,
            aws_cfg=cfg.provider_cfg,
            embeddings=embeddings
        )

    if cfg.cloud_provider == CloudProvider.AZURE:
        from streamlit_app.vector.cosmosdb import build_cosmosdb_store

        if not isinstance(cfg.provider_cfg, AzureConfig):
            raise TypeError(f"Expected AzureConfig for Azure provider, got {type(cfg.provider_cfg).__name__}")

        return build_cosmosdb_store(
            cosmos_cfg=cfg.provider_cfg.cosmos_config,
            embeddings=embeddings
        )

    if cfg.cloud_provider == CloudProvider.GCP:

        if not isinstance(cfg.provider_cfg, AzureConfig):
            raise TypeError(f"Expected AzureConfig for Azure provider, got {type(cfg.provider_cfg).__name__}")

        raise NotImplementedError("GCP vector store not implemented.")


    raise NotImplementedError(f"Vector store not implemented for provider: {cfg.cloud_provider.value}")
