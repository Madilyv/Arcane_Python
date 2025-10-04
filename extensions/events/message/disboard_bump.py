# extensions/events/message/disboard_bump.py
"""
Event listener for Disboard bump messages.
Tracks bumps, stores to MongoDB, and sends thank you messages with review reminders.
"""

import hikari
import lightbulb
from datetime import datetime, timezone
from typing import Optional

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    LinkButtonBuilder as LinkButton,
    MessageActionRowBuilder as ActionRow,
)

from utils.mongo import MongoClient
from utils.constants import (
    GREEN_ACCENT,
    DISBOARD_BOT_ID,
    BUMP_CHANNEL_ID,
    DISBOARD_REVIEW_URL
)

loader = lightbulb.Loader()

# Global variables
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


@loader.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent):
    """Initialize global variables on bot startup"""
    global bot_instance
    bot_instance = event.app
    print("[Disboard Bump] Event listener initialized")


@loader.listener(hikari.GuildMessageCreateEvent)
@lightbulb.di.with_di
async def on_disboard_bump(
        event: hikari.GuildMessageCreateEvent,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED
):
    """Listen for Disboard bump confirmation messages"""
    global mongo_client, bot_instance

    # Initialize if needed
    if not mongo_client:
        mongo_client = mongo
    if not bot_instance:
        bot_instance = bot

    # Only process messages in the bump channel
    if event.channel_id != BUMP_CHANNEL_ID:
        return

    # Only process messages from Disboard bot
    if not event.is_bot or event.author_id != DISBOARD_BOT_ID:
        return

    print(f"[Disboard Bump] Detected Disboard message in bump channel")

    # Check if this is a successful bump message
    # Disboard sends an embed with "Bump done!" or similar text
    is_bump_success = False
    bumper_user_id = None

    # Check message content
    if event.content and "bump done" in event.content.lower():
        is_bump_success = True

    # Check embeds (Disboard uses embeds for bump confirmations)
    if event.message.embeds:
        for embed in event.message.embeds:
            # Check description for bump confirmation
            if embed.description and "bump done" in embed.description.lower():
                is_bump_success = True

                # Try to extract user mention from description
                # Disboard typically mentions the user who bumped
                if event.message.user_mentions:
                    # Get the first mentioned user (the bumper)
                    bumper_user_id = list(event.message.user_mentions.keys())[0]

                break

    if not is_bump_success:
        print("[Disboard Bump] Not a bump confirmation message, ignoring")
        return

    print(f"[Disboard Bump] Bump confirmed! Message ID: {event.message_id}")

    # Store bump data to MongoDB
    bump_data = {
        "last_bump_message_id": str(event.message_id),
        "last_bump_timestamp": datetime.now(timezone.utc),
        "last_bump_user_id": str(bumper_user_id) if bumper_user_id else None,
        "channel_id": str(event.channel_id),
        "guild_id": str(event.guild_id)
    }

    # Upsert to MongoDB (update if exists, insert if not)
    await mongo_client.disboard_bump.update_one(
        {"guild_id": str(event.guild_id)},
        {"$set": bump_data},
        upsert=True
    )

    print(f"[Disboard Bump] Stored bump data to MongoDB")

    # Delete the previous reminder message if it exists
    try:
        # Get the stored reminder message ID from MongoDB
        existing_bump_data = await mongo_client.disboard_bump.find_one({"guild_id": str(event.guild_id)})

        if existing_bump_data and existing_bump_data.get("last_reminder_message_id"):
            reminder_message_id = existing_bump_data["last_reminder_message_id"]

            try:
                # Try to delete the reminder message
                await bot.rest.delete_message(
                    BUMP_CHANNEL_ID,
                    int(reminder_message_id)
                )
                print(f"[Disboard Bump] Deleted old reminder message: {reminder_message_id}")

                # Clear the stored reminder message ID
                await mongo_client.disboard_bump.update_one(
                    {"guild_id": str(event.guild_id)},
                    {"$unset": {"last_reminder_message_id": ""}}
                )
            except hikari.NotFoundError:
                print(f"[Disboard Bump] Reminder message already deleted or not found")
                # Clear it anyway since it doesn't exist
                await mongo_client.disboard_bump.update_one(
                    {"guild_id": str(event.guild_id)},
                    {"$unset": {"last_reminder_message_id": ""}}
                )
            except Exception as e:
                print(f"[Disboard Bump] Error deleting reminder message: {e}")
    except Exception as e:
        print(f"[Disboard Bump] Error checking for reminder message: {e}")

    # Send thank you message with review reminder
    await send_bump_thank_you(event.channel_id, bumper_user_id)


async def send_bump_thank_you(channel_id: int, bumper_user_id: Optional[int] = None):
    """Send a thank you message for bumping with review reminder"""

    # Build the thank you message
    user_mention = f"<@{bumper_user_id}>" if bumper_user_id else "Someone"

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"## 🎉 Thank You for Bumping!"),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    f"{user_mention} just bumped our server! Thank you for helping "
                    f"Kings Alliance grow! 🚀"
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "### 💎 **Earn Extra Clan Points!**\n"
                    "Did you know? Your clan can gain **one extra point** for leaving a "
                    "**5-star review** with meaningful content on Disboard!"
                )),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "Help us reach more players and earn rewards for your clan by "
                    "sharing your experience with Kings Alliance!"
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                ActionRow(
                    components=[
                        LinkButton(
                            url=DISBOARD_REVIEW_URL,
                            label="Leave a 5⭐ Review",
                            emoji="⭐"
                        )
                    ]
                ),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    f"*Next bump available in 2 hours. We'll remind you when it's time!* ⏰"
                )),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    try:
        await bot_instance.rest.create_message(
            channel=channel_id,
            components=components
        )
        print("[Disboard Bump] Sent thank you message")
    except Exception as e:
        print(f"[Disboard Bump] Error sending thank you message: {e}")