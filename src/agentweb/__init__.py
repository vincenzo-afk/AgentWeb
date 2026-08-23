"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .engine import AgentWebEngine
from .scheduler import Scheduler
from .rdbms import DatabaseConfig, PostgresRelationalStore, open_relational_store
from .secrets import MappingSecretProvider, SecretProviderConfig, build_provider
from .synthesis import SynthesisResult, synthesize

__all__ = [
    "AgentWebEngine",
    "BrowserEngine",
    "BrowserSession",
    "DatabaseConfig",
    "MappingSecretProvider",
    "PostgresRelationalStore",
    "Scheduler",
    "SecretProviderConfig",
    "SynthesisResult",
    "build_provider",
    "create_server",
    "open_relational_store",
    "synthesize",
]
__version__ = "0.7.0"
