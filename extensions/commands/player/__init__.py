# extensions/commands/player/__init__.py
import lightbulb

loader = lightbulb.Loader()
player = lightbulb.Group("player", "Player-related commands and utilities")

__all__ = ["loader", "player"]
