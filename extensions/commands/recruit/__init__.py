import lightbulb

loader = lightbulb.Loader()
recruit = lightbulb.Group("recruit", "All Recruit-related commands")

# Import subcommands to ensure they're loaded
from . import bidding
from . import deny
from . import migrate_ticket_open
from . import questions
from . import verify_ticket_channels

# Register the group to the loader
loader.command(recruit)

__all__ = ["loader", "recruit"]
