import lightbulb

loader = lightbulb.Loader()
ticket = lightbulb.Group("ticket", "Manual ticket management commands")

# Import subcommands to ensure they're loaded
from . import add
from . import close
from . import create

# Register the group to the loader
loader.command(ticket)

__all__ = ["loader", "ticket"]