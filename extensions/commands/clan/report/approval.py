# extensions/commands/clan/report/approval.py
"""Approval workflow handlers for clan points"""

import hikari
import lightbulb
from datetime import datetime

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow,
    ThumbnailComponentBuilder as Thumbnail,
    SectionComponentBuilder as Section
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.constants import GREEN_ACCENT, RED_ACCENT

from .utils import LOG_CHANNEL


@register_action("approve_points", ephemeral=True)
@lightbulb.di.with_di
async def approve_points(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle point approval"""
    parts = action_id.split(":", 2)
    submission_type = parts[0]
    clan_tag = parts[1]
    user_id = parts[2]

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Clan not found in database!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Update clan points
    new_points = clan.points + 1
    await mongo.clans.update_one(
        {"tag": clan_tag},
        {"$inc": {"points": 1}}
    )

    # Format submission type for display
    submission_display = "Discord Server Posts" if submission_type == "discord_post" else "Discord DM"

    # Send to log channel
    log_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"## ✅ Approval: Clan Points - {clan.name}"),

                Section(
                    components=[
                        Text(content=(
                            f"**{clan.name}**: Awarded +1 Point submitted by\n"
                            f"<@{user_id}> for {submission_display}.\n\n"
                            f"**Current Clan Points**\n"
                            f"• Clan now has **{new_points}** points."
                        ))
                    ],
                    accessory=Thumbnail(
                        media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
                    )
                ),

                Text(
                    content=f"-# Approved by {ctx.user.mention} • Today at {datetime.now().strftime('%I:%M %p').lstrip('0')}"),

                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await bot.rest.create_message(
        channel=LOG_CHANNEL,
        components=log_components
    )

    # Send DM to user
    try:
        user = await bot.rest.fetch_user(int(user_id))
        dm_channel = await user.fetch_dm_channel()

        dm_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content=f"## ✅ Clan Points Approved!"),
                    Text(content=(
                        f"Your clan point submission for **{clan.name}** has been approved!\n\n"
                        f"**Points Awarded:** 1\n"
                        f"**Submission Type:** {submission_display}\n"
                        f"**Clan Total:** {new_points} points\n\n"
                        "Thank you for your contribution!"
                    )),
                    Media(items=[MediaItem(media="assets/Green_Footer.png")])
                ]
            )
        ]

        await bot.rest.create_message(
            channel=dm_channel.id,
            components=dm_components
        )
    except:
        pass  # User has DMs disabled

    # Delete the approval message
    await ctx.interaction.delete_initial_response()

    # Respond to approver
    await ctx.respond(
        f"✅ Approved! {clan.name} now has {new_points} points.",
        ephemeral=True
    )


@register_action("deny_points", ephemeral=True)
async def deny_points(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Show denial modal"""
    submission_type, clan_tag, user_id = action_id.split(":", 2)

    reason_input = ModalActionRow().add_text_input(
        "denial_reason",
        "Denial Reason",
        placeholder="Please provide a reason for denial...",
        required=True,
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=10,
        max_length=500
    )

    await ctx.respond_with_modal(
        title="Deny Clan Points",
        custom_id=f"submit_denial:{submission_type}:{clan_tag}:{user_id}",
        components=[reason_input]
    )


@register_action("submit_denial", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def submit_denial(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Process the denial with reason"""
    submission_type, clan_tag, user_id = action_id.split(":", 2)

    # Extract denial reason
    def get_value(custom_id: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == custom_id:
                    return comp.value
        return ""

    denial_reason = get_value("denial_reason").strip()

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Clan not found in database!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Format submission type
    submission_display = "Discord Server Posts" if submission_type == "discord_post" else "Discord DM"

    # Send to log channel
    log_components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"## ❌ Denied: Clan Points - {clan.name}"),

                Section(
                    components=[
                        Text(content=(
                            f"**{clan.name}**: Denied +1 Point submitted by\n"
                            f"<@{user_id}> for {submission_display}.\n\n"
                            f"**Current Clan Points**\n"
                            f"• Clan now has **{clan.points}** points."
                        ))
                    ],
                    accessory=Thumbnail(
                        media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
                    )
                ),

                Separator(),
                Text(content=f"**Denial Reason**\n{denial_reason}"),

                Text(
                    content=f"-# Denied by {ctx.user.mention} • Today at {datetime.now().strftime('%I:%M %p').lstrip('0')}"),

                Media(items=[MediaItem(media="assets/Red_Footer.png")])
            ]
        )
    ]

    await bot.rest.create_message(
        channel=LOG_CHANNEL,
        components=log_components
    )

    # Send DM to user
    try:
        user = await bot.rest.fetch_user(int(user_id))
        dm_channel = await user.fetch_dm_channel()

        dm_components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=f"## ❌ Clan Points Denied"),
                    Text(content=(
                        f"Your clan point submission for **{clan.name}** was not approved.\n\n"
                        f"**Submission Type:** {submission_display}\n"
                        f"**Reason:** {denial_reason}\n\n"
                        "If you have questions, please contact leadership."
                    )),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")])
                ]
            )
        ]

        await bot.rest.create_message(
            channel=dm_channel.id,
            components=dm_components
        )
    except:
        pass  # User has DMs disabled

    # Inform sender about the warning
    info_text = (
        f"⚠️ **Important:** This denial will be sent to <@{user_id}>.\n"
        "They will see your denial reason. Please ensure it's appropriate."
    )

    await ctx.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_UPDATE,
        content=info_text,
        flags=hikari.MessageFlag.EPHEMERAL
    )

    # Delete the original approval message after a delay
    import asyncio
    await asyncio.sleep(3)
    await ctx.interaction.delete_initial_response()


# Create a loader instance to ensure this module can be loaded
loader = lightbulb.Loader()