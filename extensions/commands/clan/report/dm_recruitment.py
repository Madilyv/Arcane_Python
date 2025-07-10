# commands/clan/report/dm_recruitment.py

"""DM recruitment reporting functionality"""

import hikari
import lightbulb
from datetime import datetime
from typing import Dict

loader = lightbulb.Loader()

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow,
    ThumbnailComponentBuilder as Thumbnail,
    SectionComponentBuilder as Section,
    LinkButtonBuilder as LinkButton
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.constants import BLUE_ACCENT, GREEN_ACCENT, MAGENTA_ACCENT, RED_ACCENT

from .helpers import (
    get_clan_options,
    create_progress_header,
    validate_discord_id,
    create_submission_data,
    get_clan_by_tag,
    APPROVAL_CHANNEL
)

# Temporary storage for DM recruitment data
dm_recruitment_data: Dict[str, dict] = {}

# ╔══════════════════════════════════════════════════════════╗
# ║          Show DM Recruitment Flow (Step 1)               ║
# ╚══════════════════════════════════════════════════════════╝

@lightbulb.di.with_di
async def show_dm_recruitment_flow(
        ctx: lightbulb.components.MenuContext,
        user_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED
):
    """Show the DM recruitment reporting flow - Step 1: Clan Selection"""
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=create_progress_header(1, 3, ["Select Clan", "Enter Details", "Review"])),
                Separator(),

                Text(content="## 🏰 Select Your Clan"),
                Text(content="Which clan recruited the new member?"),

                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"dm_select_clan:{user_id}",
                            placeholder="Choose a clan...",
                            options=await get_clan_options(mongo)
                        )
                    ]
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Cancel",
                            emoji="❌",
                            custom_id=f"cancel_report:{user_id}"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, edit=True)

# ╔══════════════════════════════════════════════════════════╗
# ║          Clan Selection Handler (Step 2)                 ║
# ╚══════════════════════════════════════════════════════════╝

@register_action("dm_select_clan", ephemeral=True, no_return=True, is_modal=True)
async def dm_handle_clan_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle clan selection and show details modal"""
    user_id = action_id
    selected_clan = ctx.interaction.values[0]

    discord_id_input = ModalActionRow().add_text_input(
        "discord_id",
        "Recruited User's Discord ID",
        placeholder="e.g., 123456789012345678",
        required=True,
        min_length=17,
        max_length=20
    )

    context_input = ModalActionRow().add_text_input(
        "context",
        "Recruitment Context",
        placeholder="How did you recruit this user? (e.g., 'From Reddit COC subreddit')",
        required=True,
        style=hikari.TextInputStyle.PARAGRAPH,
        max_length=200
    )

    screenshot_input = ModalActionRow().add_text_input(
        "screenshot_url",
        "Screenshot URL (Optional)",
        placeholder="Direct link to DM screenshot (imgur, discord cdn, etc.)",
        required=False,
        max_length=500
    )

    await ctx.respond_with_modal(
        title="DM Recruitment Details",
        custom_id=f"dm_submit_details:{selected_clan}_{user_id}",
        components=[discord_id_input, context_input, screenshot_input]
    )

# ╔══════════════════════════════════════════════════════════╗
# ║         DM Recruitment Details Submission (Step 3)       ║
# ╚══════════════════════════════════════════════════════════╝

@register_action("dm_submit_details", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def dm_submit_details(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Process DM recruitment details and show review"""
    parts = action_id.split("_")
    clan_tag = parts[0]
    user_id = parts[1]

    discord_id = ""
    context = ""
    screenshot_url = ""

    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "discord_id":
                discord_id = comp.value.strip()
            elif comp.custom_id == "context":
                context = comp.value.strip()
            elif comp.custom_id == "screenshot_url":
                screenshot_url = comp.value.strip()

    if not validate_discord_id(discord_id):
        await ctx.respond(
            "❌ Invalid Discord ID! Please enter a valid 17-19 digit Discord user ID.",
            ephemeral=True
        )
        return

    clan = await get_clan_by_tag(mongo, clan_tag)
    if not clan:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    session_key = f"{clan_tag}_{user_id}_{int(datetime.now().timestamp())}"
    dm_recruitment_data[session_key] = {
        "discord_id": discord_id,
        "context": context,
        "screenshot_url": screenshot_url
    }

    review_components = [
        Text(content=create_progress_header(3, 3, ["Select Clan", "Enter Details", "Review"])),
        Separator(),

        Text(content="## 📋 Review Your Submission"),

        Section(
            components=[
                Text(content=(
                    f"**Clan:** {clan.emoji if clan.emoji else ''} {clan.name}\n"
                    f"**Type:** DM Recruitment\n"
                    f"**Points to Award:** 1"
                ))
            ],
            accessory=Thumbnail(
                media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
            )
        ),

        Separator(),

        Text(content=(
            f"**📋 Recruitment Details:**\n"
            f"**Recruited User:** <@{discord_id}>\n"
            f"**Context:** {context}"
        )),
    ]

    if screenshot_url:
        review_components.extend([
            Text(content="**📸 Screenshot:**"),
            ActionRow(
                components=[
                    LinkButton(
                        label="View Screenshot",
                        url=screenshot_url,
                        emoji="🖼️"
                    )
                ]
            )
        ])

    review_components.extend([
        ActionRow(
            components=[
                Button(
                    style=hikari.ButtonStyle.SUCCESS,
                    label="Submit for Approval",
                    emoji="✅",
                    custom_id=f"dm_confirm_submit:{session_key}"
                ),
                Button(
                    style=hikari.ButtonStyle.SECONDARY,
                    label="Start Over",
                    emoji="🔄",
                    custom_id=f"cancel_report:{user_id}"
                )
            ]
        ),

        Text(content="-# Your submission will be reviewed by leadership"),

        Media(items=[MediaItem(media="assets/Green_Footer.png")])
    ])

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=review_components
        )
    ]

    await ctx.interaction.create_initial_response(hikari.ResponseType.DEFERRED_MESSAGE_UPDATE)
    await ctx.interaction.edit_initial_response(components=components)

# ╔══════════════════════════════════════════════════════════╗
# ║            Confirm Submission Handler                    ║
# ╚══════════════════════════════════════════════════════════╝

@register_action("dm_confirm_submit", no_return=True)
@lightbulb.di.with_di
async def dm_confirm_submission(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Finalize DM recruitment submission and send to approval"""
    session_key = action_id

    if session_key not in dm_recruitment_data:
        await ctx.respond("❌ Error: Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[session_key]
    parts = session_key.split("_")
    clan_tag = parts[0]
    user_id = parts[1]

    clan = await get_clan_by_tag(mongo, clan_tag)
    if not clan:
        await ctx.respond("❌ Error: Clan not found!", ephemeral=True)
        return

    approval_data = await create_submission_data(
        submission_type="DM Recruitment",
        clan=clan,
        user=ctx.user,
        discord_id=data['discord_id'],
        context=data['context'],
        screenshot_url=data.get('screenshot_url')
    )

    approval_components_list = [
        Text(content="## 🔔 Clan Points Submission"),

        Section(
            components=[
                Text(content=(
                    f"**Submitted by:** {approval_data['user_mention']}\n"
                    f"**Clan:** {approval_data['clan_name']}\n"
                    f"**Type:** DM Recruitment\n"
                    f"**Time:** <t:{approval_data['timestamp']}:R>"
                ))
            ],
            accessory=Thumbnail(media=approval_data['clan_logo'])
        ),

        Separator(),

        Text(content=(
            f"**📋 Recruitment Details:**\n"
            f"**Recruited User:** <@{data['discord_id']}>\n"
            f"**Context:** {data['context']}"
        )),
    ]

    if data.get('screenshot_url'):
        approval_components_list.extend([
            Separator(),
            Text(content="**📸 Screenshot Evidence:**"),
            Media(items=[MediaItem(media=data['screenshot_url'])])
        ])

    approval_components_list.extend([
        ActionRow(
            components=[
                Button(
                    style=hikari.ButtonStyle.SUCCESS,
                    label="Approve",
                    emoji="✅",
                    custom_id=f"approve_points:dm_recruit_{clan_tag}_{user_id}"
                ),
                Button(
                    style=hikari.ButtonStyle.DANGER,
                    label="Deny",
                    emoji="❌",
                    custom_id=f"deny_points:dm_recruit_{clan_tag}_{user_id}"
                )
            ]
        ),
        Media(items=[MediaItem(media="assets/Purple_Footer.png")])
    ])

    approval_components = [
        Container(
            accent_color=MAGENTA_ACCENT,
            components=approval_components_list
        )
    ]

    try:
        await bot.rest.create_message(
            channel=APPROVAL_CHANNEL,
            components=approval_components
        )

        del dm_recruitment_data[session_key]

        success_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content="## ✅ Submission Sent!"),
                    Text(content=(
                        f"Your DM recruitment submission for **{clan.name}** has been sent for approval.\n\n"
                        "You'll receive a DM once it's been reviewed by leadership."
                    )),

                    ActionRow(
                        components=[
                            Button(
                                style=hikari.ButtonStyle.PRIMARY,
                                label="Submit Another",
                                emoji="➕",
                                custom_id=f"report_another:{user_id}"
                            )
                        ]
                    ),

                    Media(items=[MediaItem(media="assets/Green_Footer.png")])
                ]
            )
        ]

        await ctx.respond(components=success_components, edit=True)

    except Exception as e:
        print(f"Error sending DM recruitment approval: {e}")
        import traceback
        traceback.print_exc()

        error_components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content="## ❌ Submission Failed"),
                    Text(content=f"Error: {str(e)}"),
                    Text(content="Please contact an administrator."),

                    ActionRow(
                        components=[
                            Button(
                                style=hikari.ButtonStyle.SECONDARY,
                                label="Try Again",
                                emoji="🔄",
                                custom_id=f"cancel_report:{user_id}"
                            )
                        ]
                    ),

                    Media(items=[MediaItem(media="assets/Red_Footer.png")])
                ]
            )
        ]
        await ctx.respond(components=error_components, edit=True)
