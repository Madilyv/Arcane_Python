# extensions/commands/player/__init__.py
import lightbulb

loader = lightbulb.Loader()
player = lightbulb.Group("player", "Player-related commands and utilities")

# Import subcommands to ensure they're loaded
from . import discord_id

# Register the group to the loader
loader.command(player)

__all__ = ["loader", "player"]
