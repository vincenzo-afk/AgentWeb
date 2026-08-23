"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .engine import AgentWebEngine
from .scheduler import Scheduler
from .rdbms import DatabaseConfig, PostgresRelationalStore, open_relational_store
from .search import JsonSearchProvider, SearchProviderConfig, SearchProviderError, build_search_provider, search
from .secrets import MappingSecretProvider, SecretProviderConfig, build_provider
from .synthesis import SynthesisResult, synthesize

__all__ = [
    "AgentWebEngine",
    "BrowserEngine",
    "BrowserSession",
    "JsonSearchProvider",
    "DatabaseConfig",
    "MappingSecretProvider",
    "PostgresRelationalStore",
    "Scheduler",
    "SearchProviderConfig",
    "SearchProviderError",
    "SecretProviderConfig",
    "SynthesisResult",
    "build_provider",
    "create_server",
    "open_relational_store",
    "synthesize",
    "build_search_provider",
    "search",
]
__version__ = "0.8.0"
