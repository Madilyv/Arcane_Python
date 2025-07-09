# commands/clan/report/dm_recruitment.py
"""DM recruitment reporting functionality"""
import hikari
import lightbulb
from datetime import datetime

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
    SectionComponentBuilder as Section
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.cloudinary_client import CloudinaryClient
from utils.classes import Clan
from utils.constants import BLUE_ACCENT, GREEN_ACCENT, MAGENTA_ACCENT

from .helpers import (
    get_clan_options,
    create_progress_header,
    create_submission_data,
    get_clan_by_tag,
    validate_discord_id,
    APPROVAL_CHANNEL
)

# Store temporary DM recruitment data (in production, use MongoDB or Redis)
dm_recruitment_data = {}


@lightbulb.di.with_di
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
                Text(content=create_progress_header(1, 4, ["Select Clan", "Add Details", "Upload Proof", "Review"])),
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

    await ctx.respond(components=components)


@register_action("dm_select_clan", ephemeral=True, no_return=True, is_modal=True)
async def dm_handle_clan_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle clan selection and show details modal"""
    user_id = action_id
    selected_clan = ctx.interaction.values[0]

    # Modal for recruitment details
    discord_id = ModalActionRow().add_text_input(
        "discord_id",
        "Recruited User's Discord ID",
        placeholder="e.g. 123456789012345678",
        required=True,
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
        custom_id=f"dm_submit_details:{selected_clan}_{user_id}",
        components=[discord_id, context]
    )


@register_action("dm_submit_details", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def dm_submit_details(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Process DM recruitment details and show upload instructions"""
    # action_id format: "clan_tag_user_id"
    parts = action_id.split("_")
    selected_clan = parts[0]
    user_id = parts[1]

    # Extract values
    discord_id = ""
    context = ""
    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "discord_id":
                discord_id = comp.value.strip()
            elif comp.custom_id == "context":
                context = comp.value.strip()

    # Validate Discord ID
    if not validate_discord_id(discord_id):
        await ctx.respond(
            "❌ Invalid Discord ID! Please enter a valid Discord user ID (17-19 digits).",
            ephemeral=True
        )
        return

    # Store data temporarily
    session_key = f"{selected_clan}_{user_id}"
    dm_recruitment_data[session_key] = {
        "discord_id": discord_id,
        "context": context,
        "clan_tag": selected_clan,
        "screenshot_url": None
    }

    # Get clan data
    clan = await get_clan_by_tag(mongo, selected_clan)
    if not clan:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

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
                            "1. Click the message field below\n"
                            "2. Click the ➕ button\n"
                            "3. Select your screenshot file\n"
                            "4. Type any message and send\n\n"
                            "*The bot will detect and process your screenshot automatically*"
                        ))
                    ]
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Skip Screenshot",
                            emoji="⏭️",
                            custom_id=f"dm_skip_proof:{session_key}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Cancel",
                            emoji="❌",
                            custom_id=f"cancel_report:{user_id}"
                        )
                    ]
                ),

                Text(content="-# Screenshots increase approval chances"),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, edit=True)


@register_action("dm_skip_proof", ephemeral=True)
@lightbulb.di.with_di
async def dm_skip_proof(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Skip screenshot and proceed to review"""
    session_key = action_id

    if session_key not in dm_recruitment_data:
        await ctx.respond("❌ Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[session_key]

    # Get clan data
    clan = await get_clan_by_tag(mongo, data['clan_tag'])
    if not clan:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    # Show review screen
    await show_dm_review_screen(ctx, session_key, clan, data)


async def show_dm_review_screen(
        ctx: lightbulb.components.MenuContext,
        session_key: str,
        clan: Clan,
        data: dict
):
    """Show the review screen for DM recruitment"""
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
                            custom_id=f"dm_confirm_submit:{session_key}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Start Over",
                            emoji="🔄",
                            custom_id=f"cancel_report:{ctx.user.id}"
                        )
                    ]
                ),

                Text(content="-# Your submission will be reviewed by leadership"),

                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, edit=True)


@register_action("dm_confirm_submit", ephemeral=True)
@lightbulb.di.with_di
async def dm_confirm_submission(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Finalize DM recruitment submission"""
    session_key = action_id

    if session_key not in dm_recruitment_data:
        await ctx.respond("❌ Session expired. Please start over.", ephemeral=True)
        return

    data = dm_recruitment_data[session_key]
    parts = session_key.split("_")
    clan_tag = parts[0]
    user_id = parts[1]

    # Get clan data
    clan = await get_clan_by_tag(mongo, clan_tag)
    if not clan:
        await ctx.respond("❌ Error: Clan not found!", ephemeral=True)
        return

    # Create submission data
    approval_data = await create_submission_data(
        submission_type="DM Recruitment",
        clan=clan,
        user=ctx.user,
        discord_id=data['discord_id'],
        context=data['context'],
        screenshot_url=data.get('screenshot_url')
    )

    # Create approval message
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

    # Add screenshot if provided
    if data.get('screenshot_url'):
        approval_components_list.extend([
            Separator(),
            Text(content="**📸 Screenshot Evidence:**"),
            Media(items=[MediaItem(media=data['screenshot_url'])])
        ])

    # Add approval buttons
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

    # Send to approval channel
    try:
        await bot.rest.create_message(
            channel=APPROVAL_CHANNEL,
            components=approval_components
        )

        # Clean up temporary data
        del dm_recruitment_data[session_key]

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

        await ctx.interaction.edit_initial_response(components=success_components)

    except Exception as e:
        await ctx.respond(
            f"❌ Error sending submission: {str(e)}",
            ephemeral=True
        )


# Handle screenshot uploads via message events (separate handler needed)
# This would go in your message event handler file
async def handle_dm_screenshot_upload(
        event: hikari.MessageCreateEvent,
        mongo: MongoClient,
        cloudinary: CloudinaryClient
):
    """Handle screenshot uploads for active DM recruitment sessions"""
    if not event.message.attachments:
        return

    # Check if user has an active DM recruitment session
    user_id = str(event.author_id)
    active_session = None

    for key, data in dm_recruitment_data.items():
        if key.endswith(f"_{user_id}"):
            active_session = key
            break

    if not active_session:
        return

    # Process first image attachment
    attachment = event.message.attachments[0]
    if attachment.media_type and attachment.media_type.startswith("image/"):
        try:
            # Upload to Cloudinary
            url = await cloudinary.upload_image(
                file_url=attachment.url,
                folder="dm_recruitment_proof",
                public_id=f"{user_id}_{int(datetime.now().timestamp())}"
            )

            # Update session data
            dm_recruitment_data[active_session]['screenshot_url'] = url

            # Delete the message to keep channel clean
            await event.message.delete()

            # Send confirmation
            await event.app.rest.create_message(
                channel=event.channel_id,
                content="✅ Screenshot uploaded! Please continue with your report.",
                user_mentions=[event.author_id],
                delete_after=10
            )

        except Exception as e:
            await event.app.rest.create_message(
                channel=event.channel_id,
                content=f"❌ Failed to upload screenshot: {str(e)}",
                user_mentions=[event.author_id],
                delete_after=10
            )