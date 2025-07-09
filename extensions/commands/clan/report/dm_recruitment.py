# extensions/commands/clan/report/dm_recruitment.py
"""DM recruitment reporting functionality"""

import hikari
import lightbulb
from datetime import datetime

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
    SectionComponentBuilder as Section
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.cloudinary_client import CloudinaryClient
from utils.classes import Clan
from utils.constants import BLUE_ACCENT, GREEN_ACCENT, MAGENTA_ACCENT

from .utils import (
    get_clan_options,
    create_progress_header,
    create_submission_data,
    APPROVAL_CHANNEL
)

# Store temporary DM recruitment data
dm_recruitment_data = {}


@register_action("dm_submit_details", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def submit_dm_details(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Process DM recruitment details"""
    selected_clan, user_id = action_id.split("_", 1)

    # Extract values
    def get_value(custom_id: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == custom_id:
                    return comp.value
        return ""

    discord_id = get_value("discord_id").strip()
    context = get_value("context").strip()

    # Store data temporarily
    dm_recruitment_data[f"{selected_clan}_{user_id}"] = {
        "discord_id": discord_id,
        "context": context,
        "clan_tag": selected_clan
    }

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": selected_clan})
    if not clan_data:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Show upload instructions
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=create_progress_header(3, 4, ["Select Clan", "Add Details", "Upload Proof", "Review"])),
                Separator(),

                Text(content="## 📸 Add Screenshot Proof"),
                Text(content=(
                    "Please upload a screenshot showing the recruitment conversation.\n"
                    "This helps verify the recruitment for point approval."
                )),

                Section(
                    components=[
                        Text(content="**📎 How to attach:**"),
                        Text(content=(
                            "1. Click the **Upload Screenshot** button below\n"
                            "2. You'll see a new message asking for the image\n"
                            "3. Click the ➕ button and select your screenshot\n"
                            "4. Send the message with the attachment"
                        ))
                    ],
                    accessory=Thumbnail(
                        media="https://cdn-icons-png.flaticon.com/512/3342/3342137.png"
                    )
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Upload Screenshot",
                            emoji="📸",
                            custom_id=f"upload_dm_proof:{selected_clan}_{user_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Skip Screenshot",
                            emoji="➡️",
                            custom_id=f"skip_dm_proof:{selected_clan}_{user_id}"
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

    await ctx.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_UPDATE,
        components=components
    )


@register_action("upload_dm_proof", ephemeral=True)
@lightbulb.di.with_di
async def upload_dm_proof(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        cloudinary: CloudinaryClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Request screenshot upload"""
    clan_tag, user_id = action_id.split("_", 1)

    # Send message requesting screenshot
    msg = await bot.rest.create_message(
        ctx.interaction.channel_id,
        f"<@{user_id}> Please upload your screenshot for the DM recruitment:",
        user_mentions=[int(user_id)]
    )

    # Store message ID for tracking
    dm_recruitment_data[f"{clan_tag}_{user_id}"]["upload_msg_id"] = msg.id

    await ctx.respond(
        "📸 Please upload your screenshot in the next message!",
        ephemeral=True
    )


@register_action("skip_dm_proof", ephemeral=True)
@lightbulb.di.with_di
async def skip_dm_proof(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Skip screenshot and proceed to review"""
    clan_tag, user_id = action_id.split("_", 1)
    key = f"{clan_tag}_{user_id}"

    if key not in dm_recruitment_data:
        await ctx.respond("❌ Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[key]

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Show review screen without screenshot
    return await create_dm_review_screen(clan, data, ctx.user)


async def create_dm_review_screen(clan: Clan, data: dict, user: hikari.User) -> list:
    """Create the review screen for DM recruitment"""
    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=create_progress_header(4, 4, ["Select Clan", "Add Details", "Upload Proof", "Review"])),
                Separator(),

                Text(content="## 📋 Review Your Submission"),

                Section(
                    components=[
                        Text(content=(
                            f"**Clan:** {clan.emoji if clan.emoji else ''} {clan.name}\n"
                            f"**Points to Award:** 1\n"
                            f"**Discord ID:** {data['discord_id']}\n"
                            f"**Screenshot:** {'✅ Uploaded' if data.get('screenshot_url') else '❌ Not provided'}"
                        ))
                    ],
                    accessory=Thumbnail(
                        media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
                    )
                ),

                Text(content=f"**Recruitment Context:**\n{data['context']}"),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Submit for Approval",
                            emoji="✅",
                            custom_id=f"confirm_dm_submit:{clan.tag}_{user.id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Start Over",
                            emoji="🔄",
                            custom_id=f"cancel_report:{user.id}"
                        )
                    ]
                ),

                Text(content="-# Your submission will be reviewed by leadership"),

                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    return components


@register_action("confirm_dm_submit", ephemeral=True)
@lightbulb.di.with_di
async def confirm_dm_submission(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Finalize DM recruitment submission"""
    clan_tag, user_id = action_id.split("_", 1)
    key = f"{clan_tag}_{user_id}"

    if key not in dm_recruitment_data:
        await ctx.respond("❌ Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[key]

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Error: Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Create submission data
    submission_data = await create_submission_data(
        submission_type="DM Recruitment",
        clan=clan,
        user=ctx.user,
        discord_id=data['discord_id'],
        context=data['context'],
        screenshot_url=data.get('screenshot_url')
    )

    # Create approval message
    approval_components = [
        Container(
            accent_color=MAGENTA_ACCENT,
            components=[
                Text(content="## 🔔 Clan Points Submission"),

                Section(
                    components=[
                        Text(content=(
                            f"**Submitted by:** {submission_data['user_mention']}\n"
                            f"**Clan:** {submission_data['clan_name']}\n"
                            f"**Type:** DM Recruitment\n"
                            f"**Time:** <t:{submission_data['timestamp']}:R>"
                        ))
                    ],
                    accessory=Thumbnail(media=submission_data['clan_logo'])
                ),

                Separator(),

                Text(content=(
                    f"**📋 Recruitment Details:**\n"
                    f"**Recruited User:** <@{data['discord_id']}>\n"
                    f"**Context:** {data['context']}"
                )),
            ]
        )
    ]

    # Add screenshot if provided
    if data.get('screenshot_url'):
        approval_components[0].components.extend([
            Separator(),
            Text(content="**📸 Screenshot Evidence:**"),
            Media(items=[MediaItem(media=data['screenshot_url'])])
        ])

    # Add approval buttons
    approval_components[0].components.extend([
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

    # Send to approval channel
    try:
        await bot.rest.create_message(
            channel=APPROVAL_CHANNEL,
            components=approval_components
        )

        # Clean up temporary data
        del dm_recruitment_data[key]

        # Update user's view to success
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

        return success_components

    except Exception as e:
        await ctx.respond(
            f"❌ Error sending submission: {str(e)}",
            ephemeral=True
        )


# Create a loader instance
loader = lightbulb.Loader()