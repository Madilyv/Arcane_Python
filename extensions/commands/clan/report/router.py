# commands/clan/report/router.py
"""Central routing and dispatch for report types"""
import hikari
import lightbulb
from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from extensions.components import register_action
from utils.constants import GOLD_ACCENT

loader = lightbulb.Loader()


async def create_home_dashboard(member: hikari.Member) -> list:
    """Create the main report dashboard"""
    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content="## 📊 Report Clan Points"),
                Text(content="Select the type of recruitment activity to report:"),

                Separator(divider=True),

                # Main report types
                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Discord Post",
                            emoji="💬",
                            custom_id=f"report_select:discord_post_{member.id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="DM Recruitment",
                            emoji="📩",
                            custom_id=f"report_select:dm_recruitment_{member.id}"
                        )
                    ]
                ),

                # Status for "Member Left" button
                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Member Left",
                            emoji="👋",
                            custom_id=f"report_select:member_left_{member.id}",
                            is_disabled=True
                        )
                    ]
                ),

                # Help section
                Separator(divider=True),
                Text(content=(
                    "**📌 Quick Guide:**\n"
                    "• **Discord Post** - You recruited via a public Discord message\n"
                    "• **DM Recruitment** - You recruited via DMs (requires screenshot)\n"
                    "• **Member Left** - *(Coming soon)*\n\n"
                    "-# Points are awarded after leadership approval"
                )),

                Media(items=[MediaItem(media="assets/Gold_Footer.png")])
            ]
        )
    ]
    return components


@register_action("report_select", ephemeral=True, no_return=True)
async def handle_report_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Route to appropriate report type handler"""
    # action_id format: "report_type_user_id"
    parts = action_id.split("_")
    if len(parts) >= 3:  # Handle dm_recruitment or other multi-word types
        report_type = f"{parts[0]}_{parts[1]}"
        user_id = parts[2]
    else:
        report_type = parts[0]
        user_id = parts[1] if len(parts) > 1 else str(ctx.user.id)

    # Verify user
    if int(user_id) != ctx.user.id:
        await ctx.respond("This button is not for you!", ephemeral=True)
        return

    # Dispatch to appropriate handler based on report type
    if report_type == "discord_post":
        from .discord_post import show_discord_post_flow
        await show_discord_post_flow(ctx, user_id)
    elif report_type == "dm_recruitment":
        from .dm_recruitment import show_dm_recruitment_flow
        await show_dm_recruitment_flow(ctx, user_id)
    elif report_type == "member_left":
        from .member_left import show_member_left_flow
        await show_member_left_flow(ctx, user_id)


@register_action("cancel_report", ephemeral=True, no_return=True)
async def cancel_report(ctx: lightbulb.components.MenuContext, action_id: str, **kwargs):
    """Universal cancel handler - returns to main dashboard"""
    user_id = action_id

    # Clean up any sessions (each module should handle its own cleanup)
    # This is just a fallback to return to dashboard

    components = await create_home_dashboard(ctx.member)
    await ctx.respond(components=components, edit=True)


@register_action("report_another", ephemeral=True, no_return=True)
async def report_another(ctx: lightbulb.components.MenuContext, action_id: str, **kwargs):
    """Handle 'Submit Another' button - returns to main dashboard"""
    components = await create_home_dashboard(ctx.member)
    await ctx.respond(components=components, edit=True)