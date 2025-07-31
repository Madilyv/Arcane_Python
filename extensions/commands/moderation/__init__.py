# extensions/commands/moderation/__init__.py
import lightbulb

loader = lightbulb.Loader()

# Import submodules to register their commands
from . import delete_old_threads

__all__ = ["loader"]