"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .credentials import BrowserCredentialStore
from .engine import AgentWebEngine
from .maintenance import purge_retention
from .metrics import MetricStore, MetricsRegistry, PostgresMetricStore
from .scheduler import Scheduler
from .rdbms import DatabaseConfig, PostgresDistributedQueue, PostgresRelationalStore, open_distributed_queue, open_relational_store
from .search import JsonSearchProvider, SearchProviderConfig, SearchProviderError, build_search_provider, search
from .secrets import MappingSecretProvider, SecretProviderConfig, build_provider
from .synthesis import SynthesisResult, synthesize

__all__ = [
    "AgentWebEngine",
    "MetricStore",
    "MetricsRegistry",
    "PostgresMetricStore",
    "purge_retention",
    "BrowserCredentialStore",
    "BrowserEngine",
    "BrowserSession",
    "JsonSearchProvider",
    "DatabaseConfig",
    "MappingSecretProvider",
    "PostgresDistributedQueue",
    "PostgresRelationalStore",
    "Scheduler",
    "SearchProviderConfig",
    "SearchProviderError",
    "SecretProviderConfig",
    "SynthesisResult",
    "build_provider",
    "create_server",
    "open_distributed_queue",
    "open_relational_store",
    "synthesize",
    "build_search_provider",
    "search",
]
__version__ = "0.11.0"
