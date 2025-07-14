# extensions/events/message/ticket_automation/handlers/timezone.py
"""
Handles timezone collection with Friend Time bot integration.
Waits for Friend Time bot confirmation of timezone setting.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
import hikari
import lightbulb

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT, GREEN_ACCENT
from ..core.state_manager import StateManager
from ..core.question_flow import QuestionFlow
from ..components.builders import create_container_component
from ..utils.constants import (
    QUESTIONNAIRE_QUESTIONS,
    TIMEZONE_CONFIRMATION_TIMEOUT
)

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None

# Friend Time bot ID
FRIEND_TIME_BOT_ID = 481439443015942166


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_timezone_question(channel_id: int, user_id: int) -> None:
    """Send the timezone question"""

    if not bot_instance:
        print("[Timezone] Error: Bot not initialized")
        return

    try:
        question_key = "timezone"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Update state
        await StateManager.set_current_question(channel_id, question_key)

        # Create components
        template = {
            "title": question_data["title"],
            "content": question_data["content"],
            "footer": "Type your response below"
        }

        components = create_container_component(
            template,
            accent_color=BLUE_ACCENT,
            user_id=user_id
        )

        # Send message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await StateManager.store_message_id(
            channel_id,
            f"questionnaire_{question_key}",
            str(msg.id)
        )

        # Mark as awaiting Friend Time confirmation
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.awaiting_friend_time": True,
                    "step_data.questionnaire.timezone_message_sent": datetime.now(timezone.utc)
                }
            }
        )

        print(f"[Timezone] Sent question to channel {channel_id}")

        # Start monitoring for Friend Time confirmation
        asyncio.create_task(monitor_friend_time_confirmation(channel_id, user_id))

    except Exception as e:
        print(f"[Timezone] Error sending question: {e}")
        import traceback
        traceback.print_exc()


async def monitor_friend_time_confirmation(channel_id: int, user_id: int) -> None:
    """Monitor for Friend Time bot confirmation"""

    print(f"[Timezone] Starting Friend Time monitoring for channel {channel_id}")

    start_time = datetime.now(timezone.utc)
    check_interval = 2  # seconds

    while (datetime.now(timezone.utc) - start_time).total_seconds() < TIMEZONE_CONFIRMATION_TIMEOUT:
        await asyncio.sleep(check_interval)

        # Check if we're still waiting
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            break

        questionnaire_data = ticket_state.get("step_data", {}).get("questionnaire", {})

        # Check if we're still on timezone question
        if questionnaire_data.get("current_question") != "timezone":
            break

        # Check if Friend Time confirmed
        if questionnaire_data.get("friend_time_confirmed", False):
            print(f"[Timezone] Friend Time confirmation received for channel {channel_id}")

            # Send success message
            await send_timezone_success_message(channel_id, user_id)

            # Move to next question
            await asyncio.sleep(3)
            await QuestionFlow.send_next_question(channel_id, user_id, "timezone")

            break

    # Timeout reached
    else:
        print(f"[Timezone] Friend Time confirmation timeout for channel {channel_id}")

        # Check one more time
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if ticket_state:
            questionnaire_data = ticket_state.get("step_data", {}).get("questionnaire", {})

            if (questionnaire_data.get("current_question") == "timezone" and
                    not questionnaire_data.get("friend_time_confirmed", False)):
                # Send manual confirmation prompt
                await send_manual_timezone_prompt(channel_id, user_id)


async def send_timezone_success_message(channel_id: int, user_id: int) -> None:
    """Send success message after timezone is set"""

    if not bot_instance:
        return

    try:
        template = {
            "title": "✅ **Timezone Set Successfully!**",
            "content": (
                "Perfect! Friend Time has recorded your timezone.\n\n"
                "*This helps us schedule clan activities at times that work for you.*"
            ),
            "footer": None
        }

        components = create_container_component(
            template,
            accent_color=GREEN_ACCENT
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(components=components, user_mentions=False)

    except Exception as e:
        print(f"[Timezone] Error sending success message: {e}")


async def send_manual_timezone_prompt(channel_id: int, user_id: int) -> None:
    """Send manual confirmation prompt if Friend Time doesn't respond"""

    if not bot_instance:
        return

    try:
        template = {
            "title": "⏰ **Timezone Confirmation**",
            "content": (
                "It looks like Friend Time might be taking a moment to respond.\n\n"
                "If you've set your timezone, we can continue!\n"
                "*Your timezone will be recorded for scheduling purposes.*"
            ),
            "footer": "Moving to the final step..."
        }

        components = create_container_component(
            template,
            accent_color=BLUE_ACCENT
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(components=components, user_mentions=False)

        # Continue anyway
        await asyncio.sleep(3)
        await QuestionFlow.send_next_question(channel_id, user_id, "timezone")

    except Exception as e:
        print(f"[Timezone] Error sending manual prompt: {e}")


async def handle_friend_time_message(message: hikari.Message) -> None:
    """Handle messages from Friend Time bot"""

    if not mongo_client or message.author.id != FRIEND_TIME_BOT_ID:
        return

    # Check if this is a timezone confirmation message
    if "timezone has been set to" in message.content.lower():
        # Friend Time confirmed a timezone setting
        channel_id = message.channel_id

        # Update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.friend_time_confirmed": True,
                    "step_data.questionnaire.awaiting_friend_time": False
                }
            }
        )

        print(f"[Timezone] Friend Time confirmation detected in channel {channel_id}")