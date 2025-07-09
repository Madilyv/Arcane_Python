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


@register_action("report_type", ephemeral=True)
@lightbulb.di.with_di
async def handle_dm_report_type(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle DM recruitment report type"""
    report_type, user_id = action_id.split(":", 1)

    if report_type == "dm_recruit":
        # Step 1: Clan Selection
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(
                        content=create_progress_header(1, 4, ["Select Clan", "Add Details", "Upload Proof", "Review"])),
                    Separator(),

                    Text(content="## 🏰 Select Your Clan"),
                    Text(content="Which clan recruited the new member?"),

                    ActionRow(
                        components=[
                            TextSelectMenu(
                                custom_id=f"select_clan:dm_recruit_{user_id}",
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
        return components


@register_action("select_clan", ephemeral=True)
async def handle_dm_clan_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle clan selection for DM recruitment"""
    report_type, user_id = action_id.split(":", 1)
    selected_clan = ctx.interaction.values[0]

    if report_type == "dm_recruit":
        # Modal for recruitment details
        player_name = ModalActionRow().add_text_input(
            "player_name",
            "New Player's Name",
            placeholder="Enter their in-game name",
            required=True,
            max_length=50
        )

        player_tag = ModalActionRow().add_text_input(
            "player_tag",
            "Player Tag (Optional)",
            placeholder="#ABC123 (if known)",
            required=False,
            max_length=20
        )

        context = ModalActionRow().add_text_input(
            "context",
            "How did you recruit them?",
            placeholder="Brief description of the recruitment",
            required=True,
            style=hikari.TextInputStyle.PARAGRAPH,
            max_length=300
        )

        await ctx.respond_with_modal(
            title="DM Recruitment Details",
            custom_id=f"dm_submit_details:{selected_clan}:{user_id}",
            components=[player_name, player_tag, context]
        )


@register_action("dm_submit_details", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def submit_dm_details(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Process DM recruitment details"""
    clan_tag, user_id = action_id.split(":", 1)

    # Extract values
    def get_value(custom_id: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == custom_id:
                    return comp.value
        return ""

    player_name = get_value("player_name").strip()
    player_tag = get_value("player_tag").strip()
    context = get_value("context").strip()

    # Store data temporarily
    dm_recruitment_data[f"{clan_tag}:{user_id}"] = {
        "player_name": player_name,
        "player_tag": player_tag,
        "context": context,
        "clan_tag": clan_tag
    }

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
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
                            "4. Send the message with your image attached"
                        ))
                    ]
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Upload Screenshot",
                            emoji="📎",
                            custom_id=f"start_upload:{clan_tag}:{user_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Skip (Not Recommended)",
                            custom_id=f"skip_upload:{clan_tag}:{user_id}"
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


@register_action("start_upload", ephemeral=True)
@lightbulb.di.with_di
async def start_upload_process(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Start the upload process"""
    clan_tag, user_id = action_id.split(":", 1)

    # Send a new message asking for the image
    upload_msg = await bot.rest.create_message(
        channel=ctx.channel_id,
        content=(
            f"{ctx.user.mention}, please upload your screenshot now!\n"
            "Click the ➕ button next to the message box and attach your image.\n"
            "-# This message will be deleted after you upload"
        )
    )

    # Store the message ID for later deletion
    dm_recruitment_data[f"{clan_tag}:{user_id}"]["upload_msg_id"] = upload_msg.id

    # Show waiting screen
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## ⏳ Waiting for Upload..."),
                Text(content="Please upload your screenshot in the message below."),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="I've Uploaded",
                            emoji="✅",
                            custom_id=f"check_upload:{clan_tag}:{user_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Skip Upload",
                            custom_id=f"skip_upload:{clan_tag}:{user_id}"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


@register_action("check_upload", ephemeral=True)
@lightbulb.di.with_di
async def check_for_upload(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        cloudinary: CloudinaryClient = lightbulb.di.INJECTED,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Check if user uploaded an image"""
    clan_tag, user_id = action_id.split(":", 1)
    key = f"{clan_tag}:{user_id}"

    if key not in dm_recruitment_data:
        await ctx.respond("❌ Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[key]

    # Get recent messages from the channel
    messages = await bot.rest.fetch_messages(ctx.channel_id).limit(10).reversed()

    # Look for a message from the user with an attachment
    image_url = None
    for msg in messages:
        if msg.author.id == int(user_id) and msg.attachments:
            for attachment in msg.attachments:
                if attachment.media_type and attachment.media_type.startswith('image'):
                    # Upload to Cloudinary
                    try:
                        uploaded = await cloudinary.upload_from_url(
                            url=attachment.url,
                            folder="clan_recruitment_proofs",
                            resource_type="image"
                        )
                        image_url = uploaded['secure_url']

                        # Delete the message with the image
                        await bot.rest.delete_message(ctx.channel_id, msg.id)

                        # Delete the upload instruction message if it exists
                        if 'upload_msg_id' in data:
                            try:
                                await bot.rest.delete_message(ctx.channel_id, data['upload_msg_id'])
                            except:
                                pass

                        break
                    except Exception as e:
                        await ctx.respond(f"❌ Failed to process image: {str(e)}", ephemeral=True)
                        return

            if image_url:
                break

    if not image_url:
        await ctx.respond(
            "❌ No image found! Please upload a screenshot first.",
            ephemeral=True
        )
        return

    # Store the image URL
    data['screenshot_url'] = image_url

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Show review screen
    return await create_dm_review_screen(clan, data, ctx.user)


@register_action("skip_upload", ephemeral=True)
@lightbulb.di.with_di
async def skip_upload(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Skip the upload process"""
    clan_tag, user_id = action_id.split(":", 1)
    key = f"{clan_tag}:{user_id}"

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
                            f"**Player Name:** {data['player_name']}\n"
                            f"**Player Tag:** {data.get('player_tag', 'Not provided')}\n"
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
                            custom_id=f"confirm_dm_submit:{clan.tag}:{user.id}"
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
    clan_tag, user_id = action_id.split(":", 1)
    key = f"{clan_tag}:{user_id}"

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
        player_name=data['player_name'],
        player_tag=data.get('player_tag'),
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
                    f"**Player:** {data['player_name']} {f'({data["player_tag"]})' if data.get('player_tag') else ''}\n"
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
                    custom_id=f"approve_points:dm_recruit:{clan_tag}:{user_id}"
                ),
                Button(
                    style=hikari.ButtonStyle.DANGER,
                    label="Deny",
                    emoji="❌",
                    custom_id=f"deny_points:dm_recruit:{clan_tag}:{user_id}"
                )
            ]
        ),
        Media(items=[MediaItem(media="assets/Magenta_Footer.png")])
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

