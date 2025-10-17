# extensions/commands/clan/__init__.py
import lightbulb

loader = lightbulb.Loader()
clan = lightbulb.Group("clan", "All Clan-related commands")

# Import subcommands to ensure they're loaded
from . import list
from . import round_table
from . import upload
from .dashboard import dashboard
from .info_hub import info
from .report import __init__ as report

# Register the group to the loader
loader.command(clan)

__all__ = ["loader", "clan"]
