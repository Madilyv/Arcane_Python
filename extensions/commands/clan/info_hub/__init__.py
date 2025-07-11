# extensions/commands/clan/info_hub/__init__.py

# Import the command to make it available when the package is imported
from .info import loader, clan

# Import handlers to ensure they are registered
from . import handlers

__all__ = ["loader", "clan"]