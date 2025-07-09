"""Discord post reporting functionality"""

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
    SectionComponentBuilder as Section,
    LinkButtonBuilder as LinkButton
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.constants import BLUE_ACCENT, GREEN_ACCENT, RED_ACCENT, MAGENTA_ACCENT

from .utils import (
    get_clan_options,
    create_progress_header,
    parse_discord_link,
    create_submission_data,
    APPROVAL_CHANNEL
)

loader = lightbulb.Loader()

@register_action("report_type", ephemeral=True)
@lightbulb.di.with_di
async def handle_report_type(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle report type selection"""
    # Split the action_id which is in format: discord_post_12345 or dm_recruit_12345
    parts = action_id.split("_")
    if len(parts) >= 2 and parts[0] in ["discord", "dm", "member"]:
        # Handle multi-word report types
        if parts[0] == "discord":
            report_type = "discord_post"
            user_id = parts[2] if len(parts) > 2 else ctx.user.id
        elif parts[0] == "dm":
            report_type = "dm_recruit"
            user_id = parts[2] if len(parts) > 2 else ctx.user.id
        elif parts[0] == "member":
            report_type = "member_left"
            user_id = parts[2] if len(parts) > 2 else ctx.user.id
    else:
        # Fallback for single word types
        report_type = parts[0]
        user_id = parts[1] if len(parts) > 1 else ctx.user.id

    # Verify user
    if int(user_id) != ctx.user.id:
        await ctx.respond("This button is not for you!", ephemeral=True)
        return

    if report_type == "discord_post":
        # Step 1: Clan Selection
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    # Progress indicator
                    Text(content=create_progress_header(1, 3, ["Select Clan", "Add Link", "Review"])),
                    Separator(),

                    Text(content="## 🏰 Select Your Clan"),
                    Text(content="Which clan recruited the new member?"),

                    ActionRow(
                        components=[
                            TextSelectMenu(
                                custom_id=f"select_clan:discord_post_{user_id}",
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

    elif report_type == "dm_recruit":
        # Step 1: Clan Selection for DM recruitment
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

    elif report_type == "member_left":
        # Not implemented yet
        await ctx.respond(
            "This feature is coming soon! For now, please contact leadership directly.",
            ephemeral=True
        )
        return


@register_action("select_clan", ephemeral=True)
async def handle_clan_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle clan selection and show appropriate next step"""
    # Split action_id which is in format: discord_post_12345 or dm_recruit_12345
    parts = action_id.split("_")
    if parts[0] == "discord":
        report_type = "discord_post"
        user_id = parts[2] if len(parts) > 2 else ctx.user.id
    elif parts[0] == "dm":
        report_type = "dm_recruit"
        user_id = parts[2] if len(parts) > 2 else ctx.user.id
    else:
        report_type = parts[0]
        user_id = parts[1] if len(parts) > 1 else ctx.user.id

    selected_clan = ctx.interaction.values[0]

    if report_type == "discord_post":
        # Modal for Discord link
        link_input = ModalActionRow().add_text_input(
            "discord_link",
            "Discord Message Link",
            placeholder="https://discord.com/channels/.../.../.../",
            required=True,
            min_length=20
        )

        notes_input = ModalActionRow().add_text_input(
            "notes",
            "Additional Notes (Optional)",
            placeholder="Any additional context for the reviewers?",
            required=False,
            style=hikari.TextInputStyle.PARAGRAPH,
            max_length=200
        )

        await ctx.respond_with_modal(
            title="Add Discord Message Link",
            custom_id=f"submit_link:{selected_clan}_{user_id}",
            components=[link_input, notes_input]
        )

    elif report_type == "dm_recruit":
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
            custom_id=f"dm_submit_details:{selected_clan}_{user_id}",
            components=[player_name, player_tag, context]
        )


@register_action("submit_link", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def submit_discord_link(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Process Discord link submission"""
    # Split action_id in format: clan_tag_user_id
    parts = action_id.split("_")
    clan_tag = parts[0]
    user_id = parts[1] if len(parts) > 1 else ctx.user.id

    # Extract values from modal
    def get_value(custom_id: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == custom_id:
                    return comp.value
        return ""

    discord_link = get_value("discord_link").strip()
    notes = get_value("notes").strip()

    # Validate Discord link
    link_data = parse_discord_link(discord_link)
    if not link_data:
        await ctx.respond(
            "❌ Invalid Discord message link! Please use a valid link format:\n"
            "`https://discord.com/channels/guild_id/channel_id/message_id`",
            ephemeral=True
        )
        return

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Store the discord link temporarily in a dict (you might want to use mongo for this in production)
    submission_data = {
        "discord_link": discord_link,
        "notes": notes
    }

    # Store in mongo button_store for retrieval
    submission_id = f"{clan_tag}_{ctx.user.id}_{int(datetime.now().timestamp())}"
    await mongo.button_store.insert_one({
        "_id": submission_id,
        "data": submission_data
    })

    # Show review screen
    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=create_progress_header(3, 3, ["Select Clan", "Add Link", "Review"])),
                Separator(),

                Text(content="## 📋 Review Your Submission"),

                Section(
                    components=[
                        Text(content=(
                            f"**Clan:** {clan.emoji if clan.emoji else ''} {clan.name}\n"
                            f"**Points to Award:** 1\n"
                            f"**Evidence:** [Discord Message]({discord_link})\n"
                            f"**Notes:** {notes if notes else 'None'}"
                        ))
                    ],
                    accessory=Thumbnail(
                        media=clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png"
                    )
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Submit for Approval",
                            emoji="✅",
                            custom_id=f"confirm_discord_submit:{submission_id}"
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

    await ctx.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_UPDATE,
        components=components
    )


@register_action("confirm_discord_submit", ephemeral=True)
@lightbulb.di.with_di
async def confirm_discord_submission(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Finalize Discord post submission and send to approval"""
    submission_id = action_id

    # Retrieve stored submission data
    stored_data = await mongo.button_store.find_one({"_id": submission_id})
    if not stored_data or "data" not in stored_data:
        await ctx.respond("❌ Error: Submission data not found!", ephemeral=True)
        return

    submission_data = stored_data["data"]
    discord_link = submission_data.get("discord_link", "")

    # Parse submission_id to get clan_tag and user_id
    parts = submission_id.split("_")
    clan_tag = parts[0]
    user_id = parts[1]

    # Clean up stored data
    await mongo.button_store.delete_one({"_id": submission_id})

    # Get clan data
    clan_data = await mongo.clans.find_one({"tag": clan_tag})
    if not clan_data:
        await ctx.respond("❌ Error: Clan not found!", ephemeral=True)
        return

    clan = Clan(data=clan_data)

    # Create submission data
    submission_data = await create_submission_data(
        submission_type="Discord Post",
        clan=clan,
        user=ctx.user,
        discord_link=discord_link
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
                            f"**Type:** Discord Post\n"
                            f"**Time:** <t:{submission_data['timestamp']}:R>"
                        ))
                    ],
                    accessory=Thumbnail(media=submission_data['clan_logo'])
                ),

                Separator(),

                Text(content="**📌 Discord Post Link:**"),

                ActionRow(
                    components=[
                        LinkButton(
                            label="View Discord Post",
                            url=discord_link,
                            emoji="🔗"
                        )
                    ]
                ),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Approve",
                            emoji="✅",
                            custom_id=f"approve_points:discord_post_{clan_tag}_{user_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.DANGER,
                            label="Deny",
                            emoji="❌",
                            custom_id=f"deny_points:discord_post_{clan_tag}_{user_id}"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Magenta_Footer.png")])
            ]
        )
    ]

    # Send to approval channel
    try:
        await bot.rest.create_message(
            channel=APPROVAL_CHANNEL,
            components=approval_components
        )

        # Update user's view to success
        success_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content="## ✅ Submission Sent!"),
                    Text(content=(
                        f"Your clan point submission for **{clan.name}** has been sent for approval.\n\n"
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


@register_action("cancel_report", ephemeral=True)
async def cancel_report(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Cancel the reporting process"""
    user_id = action_id

    # Return to home dashboard
    from .utils import create_home_dashboard
    return await create_home_dashboard(ctx.member)


@register_action("report_another", ephemeral=True)
async def report_another(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Start another report"""
    # Return to home dashboard
    from .utils import create_home_dashboard
    return await create_home_dashboard(ctx.member)


# Create a loader instance to ensure this module can be loaded
loader = lightbulb.Loader()