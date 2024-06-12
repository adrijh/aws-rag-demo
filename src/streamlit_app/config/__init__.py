from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Self

from streamlit_app.config.providers import AWSConfig, AzureConfig, GCPConfig

type ProviderConfig = AWSConfig | AzureConfig | GCPConfig

class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

@dataclass
class Config:
    cloud_provider: CloudProvider
    is_local: bool
    provider_cfg: ProviderConfig

    PROVIDER_CONFIG_MAP: MappingProxyType[CloudProvider, type[ProviderConfig]] = MappingProxyType(
        {
            CloudProvider.AWS: AWSConfig,
            CloudProvider.AZURE: AzureConfig,
            CloudProvider.GCP: GCPConfig,
        }
    )

    @classmethod
    def from_env(cls) -> Self:
        cloud_provider = cls.get_cloud_provider()
        provider_cfg = cls.get_provider_config(cloud_provider)

        return cls(
            cloud_provider=cloud_provider,
            is_local=os.getenv("IS_LOCAL", "false").lower() == "true",
            provider_cfg=provider_cfg,
        )

    @classmethod
    def get_cloud_provider(cls) -> CloudProvider:
        provider_env = os.getenv("CLOUD_PROVIDER", "aws").lower()
        return CloudProvider(provider_env)

    @classmethod
    def get_provider_config(cls, provider: CloudProvider) -> ProviderConfig:
        return cls.PROVIDER_CONFIG_MAP[provider].from_env()
