import os
from dataclasses import dataclass
from typing import Self


@dataclass
class AWSConfig:
    aws_region: str
    opensearch_endpoint: str
    opensearch_index_name: str

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            aws_region=os.environ["AWS_REGION"],
            opensearch_endpoint=os.environ["OPENSEARCH_ENDPOINT"],
            opensearch_index_name=os.environ["OPENSEARCH_INDEX_NAME"],
        )


@dataclass
class CosmosConfig:
    user: str
    password: str
    connection_string: str
    db_name: str
    collection_name: str
    index_name: str
    namespace: str

    @classmethod
    def from_env(cls) -> Self:
        user = os.environ["COSMOS_USERNAME"]
        password = cls.get_cosmos_password()
        db_name = os.environ["COSMOS_DB_NAME"]
        collection_name = os.environ["COSMOS_COLLECTION_NAME"]

        cosmos_connection_string_base = (
            "mongodb+srv://<user>:<password>@transcription-demo.mongocluster.cosmos.azure.com/"
            "?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
        )

        connection_string = (
            cosmos_connection_string_base
            .replace("<user>", user)
            .replace("<password>", password)
        )

        namespace = f"{db_name}.{collection_name}"

        return cls(
            user=user,
            password=password,
            connection_string=connection_string,
            db_name=db_name,
            collection_name=collection_name,
            index_name=os.environ["COSMOS_INDEX_NAME"],
            namespace=namespace,
        )

    @classmethod
    def get_cosmos_password(cls):
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        key_vault_uri = os.environ["KEY_VAULT_URI"]
        secret_name = os.environ["COSMOS_SECRET"]

        client = SecretClient(
            vault_url=key_vault_uri,
            credential=DefaultAzureCredential(),
        )

        return client.get_secret(secret_name).value


@dataclass
class AzureConfig:
    cosmos_config: CosmosConfig

    @classmethod
    def from_env(cls) -> Self:
        cosmos_config = CosmosConfig.from_env()

        return cls(
            cosmos_config=cosmos_config,
        )

@dataclass
class GCPConfig:
    @classmethod
    def from_env(cls) -> Self:
        raise NotImplementedError("Google Cloud Platform provider not implemented.")
