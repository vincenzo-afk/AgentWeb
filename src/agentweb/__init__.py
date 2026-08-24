"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .browser_sessions import BrowserSessionStore
from .connectors import Connector, ConnectorRegistry
from .credentials import BrowserCredentialStore
from .engine import AgentWebEngine
from .graph import Entity, GraphResult, GraphStore, Relation
from .maintenance import purge_retention
from .metrics import MetricStore, MetricsRegistry, PostgresMetricStore
from .planner import Plan, PlanStep, PlanStore, Planner, StoredPlan
from .router import Router, ToolCall, route
from .scheduler import Scheduler
from .skills import Skill, SkillRegistry, match_skill, register_skill
from .rdbms import DatabaseConfig, PostgresDistributedQueue, PostgresRelationalStore, open_distributed_queue, open_relational_store
from .search import JsonSearchProvider, SearchProviderConfig, SearchProviderError, build_search_provider, search
from .secrets import MappingSecretProvider, SecretProviderConfig, build_provider
from .synthesis import SynthesisResult, synthesize
from .workflows import WorkflowStore

__all__ = [
    "AgentWebEngine",
    "Connector",
    "ConnectorRegistry",
    "Entity",
    "GraphResult",
    "GraphStore",
    "Relation",
    "MetricStore",
    "MetricsRegistry",
    "PostgresMetricStore",
    "Plan",
    "PlanStep",
    "Planner",
    "PlanStore",
    "StoredPlan",
    "Router",
    "Skill",
    "SkillRegistry",
    "ToolCall",
    "match_skill",
    "purge_retention",
    "BrowserCredentialStore",
    "BrowserSessionStore",
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
    "WorkflowStore",
    "route",
    "register_skill",
    "build_search_provider",
    "search",
]
__version__ = "0.11.0"
