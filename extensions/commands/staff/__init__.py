# extensions/commands/staff/__init__.py
import lightbulb

loader = lightbulb.Loader()
staff = lightbulb.Group("staff", "All Staff-related commands")

# Import subcommands
from . import quizzes

# Register the group
loader.command(staff)

__all__ = ["loader", "staff"]
