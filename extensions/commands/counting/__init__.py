# extensions/commands/counting/__init__.py
import lightbulb

loader = lightbulb.Loader()
counting = lightbulb.Group("counting", "Counting channel commands")

# Import submodules to register commands
from . import set_number
from . import toggle
from . import status

# Register the counting group
loader.command(counting)

__all__ = ["loader", "counting"]