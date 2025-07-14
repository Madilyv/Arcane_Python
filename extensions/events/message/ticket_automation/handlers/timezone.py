# extensions/events/message/ticket_automation/handlers/timezone.py
"""
Timezone handler using Friend Time bot integration.
"""

import asyncio
from typing import Optional
from datetime import datetime, timezone as tz
import hikari

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    SectionComponentBuilder as Section,
    LinkButtonBuilder as LinkButton,
)

from utils.mongo import MongoClient
from utils.emoji import emojis
from utils.constants import BLUE_ACCENT
from ..core.state_manager import StateManager
from ..utils.constants import TIMEZONE_CONFIRMATION_TIMEOUT, QUESTIONNAIRE_QUESTIONS

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None

# Friend Time bot configuration
FRIEND_TIME_BOT_ID = 481439443015942166
FRIEND_TIME_SET_COMMAND_ID = 924862149292085268


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize handler with required instances."""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_timezone_question(channel_id: int, user_id: int) -> None:
    """Send the timezone question with Friend Time bot instructions."""

    if not mongo_client or not bot_instance:
        print("[Timezone] Error: Not initialized")
        return

    try:
        # Update state using StateManager classmethod
        await StateManager.set_current_question(channel_id, "timezone")

        # Also set timezone-specific flags
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.awaiting_response": False,
                    "step_data.questionnaire.awaiting_timezone_confirmation": True
                }
            }
        )

        question_data = QUESTIONNAIRE_QUESTIONS["timezone"]

        # Build components
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"<@{user_id}>"),
                    Separator(divider=True),
                    Text(content=question_data["title"]),
                    Separator(divider=True),
                    Text(content=(
                        "To help us match you with the right clan and events, let's set your timezone.\n\n"
                    )),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**Step 1: Find Your Time Zone**"
                                )
                            )
                        ],
                        accessory=LinkButton(
                            url="https://zones.arilyn.cc/",
                            label="Get My Time Zone 🌐",
                        ),
                    ),
                    Text(
                        content=(
                            "**Example format:** `America/New_York`\n\n"
                            "**Steps:**\n"
                            "1. Click the link above to find your timezone\n"
                            f"2. Use the command: </set me:{FRIEND_TIME_SET_COMMAND_ID}>\n"
                            "3. Paste your timezone when Friend Time bot asks\n"
                            "4. Confirm with **yes** when prompted\n\n"
                            "*I'll wait for Friend Time bot to confirm your timezone is set!*"
                        )
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")]),
                    Text(content="-# Kings Alliance Recruitment – Syncing Schedules, Building Teams!")
                ]
            )
        ]

        # Send message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await StateManager.store_message_id(
            channel_id,
            f"questionnaire_timezone",
            str(msg.id)
        )

        # Start monitoring for Friend Time confirmation
        asyncio.create_task(
            monitor_friend_time_confirmation(channel_id, user_id)
        )

        print(f"[Timezone] Sent timezone question to channel {channel_id}")

    except Exception as e:
        print(f"[Timezone] Error sending timezone question: {e}")
        import traceback
        traceback.print_exc()


async def monitor_friend_time_confirmation(channel_id: int, user_id: int):
    """Monitor for Friend Time bot confirmation with timeout."""
    try:
        print(f"[Timezone] Starting Friend Time monitor for channel {channel_id}")

        # Wait for the configured timeout
        await asyncio.sleep(TIMEZONE_CONFIRMATION_TIMEOUT)

        # Check if we're still waiting
        current_state = await StateManager.get_ticket_state(str(channel_id))
        if (current_state and
                current_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_timezone_confirmation",
                                                                                False)):

            print(
                f"[Timezone] Friend Time confirmation timeout after {TIMEZONE_CONFIRMATION_TIMEOUT}s - proceeding anyway")

            # Mark as complete with timeout
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.awaiting_timezone_confirmation": False,
                        "step_data.questionnaire.timezone": "Not set (timeout)",
                        "step_data.questionnaire.responses.timezone": "Not set (timeout)"
                    }
                }
            )

            # Move to next question
            from ..core import questionnaire_manager
            next_question = QUESTIONNAIRE_QUESTIONS["timezone"]["next"]
            if next_question:
                await questionnaire_manager.send_question(channel_id, user_id, next_question)

    except Exception as e:
        print(f"[Timezone] Error in Friend Time monitor: {e}")
        import traceback
        traceback.print_exc()


async def check_friend_time_confirmation(event: hikari.GuildMessageCreateEvent) -> bool:
    """
    Check if a message is a Friend Time bot timezone confirmation.
    This function should be called from message event listeners.
    """
    # Only check bot messages
    if not event.is_bot:
        return False

    # Check if it's from Friend Time bot
    if event.author_id != FRIEND_TIME_BOT_ID:
        return False

    # Get ticket state
    ticket_state = await StateManager.get_ticket_state(str(event.channel_id))
    if not ticket_state:
        return False

    # Check if we're waiting for timezone confirmation
    if not ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_timezone_confirmation", False):
        return False

    print(f"[Timezone] Checking Friend Time message in channel {event.channel_id}")

    # Look for confirmation patterns
    is_confirmed = False
    timezone_value = None

    # Check message content
    if event.content:
        confirmation_phrases = [
            "Successfully set your time zone",
            "Your time zone has been set",
            "Time zone updated",
            "Congratulations!",
            "You've completed user setup!"
        ]

        for phrase in confirmation_phrases:
            if phrase in event.content:
                is_confirmed = True
                break

        # Try to extract timezone
        if is_confirmed:
            import re
            timezone_pattern = r'([A-Za-z_]+\/[A-Za-z_]+(?:\/[A-Za-z_]+)?)'
            match = re.search(timezone_pattern, event.content)
            if match:
                timezone_value = match.group(1)

    # Check embeds
    if event.message.embeds:
        for embed in event.message.embeds:
            if embed.description:
                for phrase in ["Successfully set", "time zone has been set", "Time zone updated"]:
                    if phrase in embed.description:
                        is_confirmed = True
                        break

            # Look for timezone in fields
            if embed.fields and is_confirmed:
                for field in embed.fields:
                    if "time zone" in field.name.lower() or "timezone" in field.name.lower():
                        timezone_value = field.value.strip()
                        break

    if is_confirmed:
        print(f"[Timezone] Friend Time confirmation detected! Timezone: {timezone_value or 'not extracted'}")

        # Update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(event.channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.timezone_confirmed": True,
                    "step_data.questionnaire.awaiting_timezone_confirmation": False,
                    "step_data.questionnaire.timezone": timezone_value or "Set (not extracted)",
                    "step_data.questionnaire.responses.timezone": timezone_value or "Set (not extracted)"
                }
            }
        )

        # Get user ID from state
        user_id = ticket_state.get("discord_id") or ticket_state.get("user_id")
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                user_id = None

        if user_id:
            # Send completion message after brief delay
            await asyncio.sleep(2)

            # Move to next question
            from ..core import questionnaire_manager
            next_question = QUESTIONNAIRE_QUESTIONS["timezone"]["next"]
            if next_question:
                await questionnaire_manager.send_question(event.channel_id, user_id, next_question)

        return True

    return False