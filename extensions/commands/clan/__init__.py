# extensions/commands/clan/__init__.py
import lightbulb

loader = lightbulb.Loader()
clan = lightbulb.Group("clan", "All Clan-related commands")

# Register the clan group once after all subcommands are loaded
loader.command(clan)

__all__ = ["loader", "clan"]
