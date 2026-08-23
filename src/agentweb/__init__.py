"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .engine import AgentWebEngine
from .scheduler import Scheduler
from .rdbms import DatabaseConfig, PostgresRelationalStore, open_relational_store
from .secrets import MappingSecretProvider, SecretProviderConfig, build_provider

__all__ = [
    "AgentWebEngine",
    "BrowserEngine",
    "BrowserSession",
    "DatabaseConfig",
    "MappingSecretProvider",
    "PostgresRelationalStore",
    "Scheduler",
    "SecretProviderConfig",
    "build_provider",
    "create_server",
    "open_relational_store",
]
__version__ = "0.5.0"
