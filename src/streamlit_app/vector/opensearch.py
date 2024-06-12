import boto3
from langchain_community.vectorstores.opensearch_vector_search import OpenSearchVectorSearch
from langchain_core.embeddings import Embeddings
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from streamlit_app.config import Config
from streamlit_app.config.providers import AWSConfig


def build_opensearch_store(cfg: Config, aws_cfg: AWSConfig, embeddings: Embeddings):
    if cfg.is_local:
        return OpenSearchVectorSearch(
            embedding_function=embeddings,
            opensearch_url=aws_cfg.opensearch_endpoint,
            index_name=aws_cfg.opensearch_index_name,
        )

    awsauth = AWS4Auth(
        refreshable_credentials=boto3.Session().get_credentials(),
        service="es",
        region=aws_cfg.aws_region,
    )
    return OpenSearchVectorSearch(
        embedding_function=embeddings,
        opensearch_url=aws_cfg.opensearch_endpoint,
        http_auth=awsauth,
        timeout=300,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        index_name=aws_cfg.opensearch_index_name,
    )
