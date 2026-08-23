"""AgentWeb: a free, dependency-light internet intelligence MVP."""

from .api import create_server
from .browser import BrowserEngine, BrowserSession
from .engine import AgentWebEngine
from .scheduler import Scheduler

__all__ = ["AgentWebEngine", "BrowserEngine", "BrowserSession", "Scheduler", "create_server"]
__version__ = "0.2.0"
