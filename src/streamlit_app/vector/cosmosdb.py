from dataclasses import asdict, dataclass

from langchain_community.vectorstores.azure_cosmos_db import (
    AzureCosmosDBVectorSearch,
    CosmosDBSimilarityType,
    CosmosDBVectorSearchType,
)
from langchain_core.embeddings import Embeddings
from pymongo import MongoClient

from streamlit_app.config.providers import CosmosConfig


@dataclass
class CosmosIndexConfig:
    num_lists: int
    dimensions: int
    similarity: CosmosDBSimilarityType
    kind: CosmosDBVectorSearchType
    m: int
    ef_construction: int

def build_cosmosdb_store(cosmos_cfg: CosmosConfig, embeddings: Embeddings):
    client: MongoClient = MongoClient(cosmos_cfg.connection_string)
    collection = client[cosmos_cfg.db_name][cosmos_cfg.collection_name]


    vector_store = AzureCosmosDBVectorSearch(
        embedding=embeddings,
        collection=collection,
        index_name=cosmos_cfg.index_name,
    )

    index_cfg = CosmosIndexConfig(
        num_lists=100,
        dimensions=768,
        similarity=CosmosDBSimilarityType.COS,
        kind=CosmosDBVectorSearchType.VECTOR_IVF,
        m = 16,
        ef_construction = 64,
    )

    vector_store.create_index(
        **asdict(index_cfg)
    )

    return vector_store
