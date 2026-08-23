"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .engine import AgentWebEngine

__all__ = ["AgentWebEngine", "create_server"]
__version__ = "0.1.0"
