# commands/clan/report/approval.py
"""Approval workflow handlers for clan points"""
import hikari
import lightbulb
from datetime import datetime

loader = lightbulb.Loader()

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

from .helpers import get_clan_by_tag, LOG_CHANNEL


@register_action("approve_points", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def approve_points(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle point approval"""
    # Parse action_id format: "submission_type_clan_tag_user_id"
    parts = action_id.split("_")

    # Handle multi-word submission types
    if parts[0] == "discord" and parts[1] == "post":
        submission_type = "discord_post"
        clan_tag = parts[2]
        user_id = parts[3]
    elif parts[0] == "dm" and parts[1] == "recruit":
        submission_type = "dm_recruit"
        clan_tag = parts[2]
        user_id = parts[3]
    else:
        submission_type = parts[0]
        clan_tag = parts[1]
        user_id = parts[2]

    # Get clan data
    clan = await get_clan_by_tag(mongo, clan_tag)
    if not clan:
        await ctx.respond("❌ Clan not found in database!", ephemeral=True)
        return

    # Update clan points
    new_points = clan.points + 1
    await mongo.clans.update_one(
        {"tag": clan_tag},
        {"$inc": {"points": 1}}
    )

    # Update recruit count for DM recruitment
    if submission_type == "dm_recruit":
        await mongo.clans.update_one(
            {"tag": clan_tag},
            {"$inc": {"recruit_count": 1}}
        )

    # Format submission type for display
    submission_display = {
        "discord_post": "Discord Server Posts",
        "dm_recruit": "Discord DM",
        "member_left": "Member Left"
    }.get(submission_type, submission_type)

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


@register_action("deny_points", ephemeral=True, no_return=True, is_modal=True)
async def deny_points(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Show denial modal"""
    # Parse action_id (same format as approve_points)
    parts = action_id.split("_")

    # Handle multi-word submission types
    if parts[0] == "discord" and parts[1] == "post":
        submission_type = "discord_post"
        clan_tag = parts[2]
        user_id = parts[3]
    elif parts[0] == "dm" and parts[1] == "recruit":
        submission_type = "dm_recruit"
        clan_tag = parts[2]
        user_id = parts[3]
    else:
        submission_type = parts[0]
        clan_tag = parts[1]
        user_id = parts[2]

    reason_input = ModalActionRow().add_text_input(
        "denial_reason",
        "Denial Reason",
        placeholder="Please provide a reason for denying this submission",
        required=True,
        style=hikari.TextInputStyle.PARAGRAPH,
        max_length=500
    )

    await ctx.respond_with_modal(
        title="Deny Clan Points Submission",
        custom_id=f"confirm_deny:{action_id}",
        components=[reason_input]
    )


@register_action("confirm_deny", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def confirm_denial(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Process denial with reason"""
    # Parse action_id (same format as approve_points)
    parts = action_id.split("_")

    # Handle multi-word submission types
    if parts[0] == "discord" and parts[1] == "post":
        submission_type = "discord_post"
        clan_tag = parts[2]
        user_id = parts[3]
    elif parts[0] == "dm" and parts[1] == "recruit":
        submission_type = "dm_recruit"
        clan_tag = parts[2]
        user_id = parts[3]
    else:
        submission_type = parts[0]
        clan_tag = parts[1]
        user_id = parts[2]

    # Extract denial reason
    reason = ""
    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "denial_reason":
                reason = comp.value.strip()

    # Get clan data
    clan = await get_clan_by_tag(mongo, clan_tag)
    if not clan:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    # Format submission type
    submission_display = {
        "discord_post": "Discord Server Posts",
        "dm_recruit": "Discord DM",
        "member_left": "Member Left"
    }.get(submission_type, submission_type)

    # Send to log channel
    log_components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"## ❌ Denial: Clan Points - {clan.name}"),

                Section(
                    components=[
                        Text(content=(
                            f"**{clan.name}**: Denied submission by\n"
                            f"<@{user_id}> for {submission_display}.\n\n"
                            f"**Reason:** {reason}"
                        ))
                    ],
                    accessory=Thumbnail(
                        media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
                    )
                ),

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
                        f"**Reason:** {reason}\n\n"
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

    # Delete the approval message
    await ctx.interaction.delete_initial_response()