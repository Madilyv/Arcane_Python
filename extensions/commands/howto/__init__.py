# extensions/commands/howto/__init__.py
import lightbulb

loader = lightbulb.Loader()
howto = lightbulb.Group("howto", "Simple guides for basic tasks")

# Import submodules to register commands
from . import link

# Register the howto group
loader.command(howto)

__all__ = ["loader", "howto"]