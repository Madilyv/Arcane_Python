# commands/clan/report/member_left.py

"""Member left reporting functionality (placeholder for future implementation)"""

import hikari
import lightbulb

loader = lightbulb.Loader()

from hikari.impl import (
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    MessageActionRowBuilder as ActionRow,
)

from extensions.components import register_action
from utils.constants import GOLD_ACCENT

# ╔══════════════════════════════════════════════════════════════╗
# ║                 Show Member Left Flow Handler                ║
# ╚══════════════════════════════════════════════════════════════╝

async def show_member_left_flow(
        ctx: lightbulb.components.MenuContext,
        user_id: str
):
    """Show member left reporting flow (coming soon)"""
    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content="## 🚧 Coming Soon!"),
                Separator(),

                Text(content=(
                    "The **Member Left** reporting feature is currently under development.\n\n"
                    "This feature will allow you to:\n"
                    "• Report when recruited members leave the clan\n"
                    "• Track retention rates\n"
                    "• Adjust point calculations accordingly\n\n"
                    "For now, please contact leadership directly if a recruited member has left."
                )),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Back to Dashboard",
                            emoji="◀️",
                            custom_id=f"cancel_report:{user_id}"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Gold_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, edit=True)

# ╔══════════════════════════════════════════════════════════════╗
# ║         Member Left Placeholder Handler (Future)             ║
# ╚══════════════════════════════════════════════════════════════╝

@register_action("member_left_flow", ephemeral=True)
async def member_left_placeholder(ctx: lightbulb.components.MenuContext, **kwargs):
    """Placeholder for member left functionality"""
    await ctx.respond(
        "This feature is coming soon! Please contact leadership directly for now.",
        ephemeral=True
    )
