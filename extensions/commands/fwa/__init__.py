import lightbulb

loader = lightbulb.Loader()
fwa = lightbulb.Group("fwa", "All FWA-related commands")

# Import subcommands to ensure they're loaded
from . import bases
from . import chocolate
from . import lazy_cwl
from . import links
from . import new_th_upgrade
from . import upload_images
from . import war_plans
from . import weight

# Register the group to the loader
loader.command(fwa)

__all__ = ["loader", "fwa"]
