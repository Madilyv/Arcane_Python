# extensions/events/message/ticket_automation/core/questionnaire_manager.py
"""
Main questionnaire manager that orchestrates the entire automation flow.
This is the primary entry point for starting and managing questionnaires.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
import hikari
import lightbulb

from utils.mongo import MongoClient
from utils.constants import GREEN_ACCENT, BLUE_ACCENT
from ..components.builders import create_container_component
from ..components.templates import INTERVIEW_SELECTION_TEMPLATE
from ..utils.constants import RECRUITMENT_STAFF_ROLE, LOG_CHANNEL_ID
from .state_manager import StateManager
from .question_flow import QuestionFlow

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the questionnaire manager with required instances"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot

    # Initialize other core modules
    StateManager.initialize(mongo, bot)
    QuestionFlow.initialize(mongo, bot)


async def send_question(channel_id: int, user_id: int, question_key: str) -> None:
    """
    Wrapper to send a specific question.
    This avoids circular imports by providing access to QuestionFlow.
    """
    await QuestionFlow.send_question(channel_id, user_id, question_key)


async def trigger_questionnaire(channel_id: int, user_id: int) -> None:
    """
    Trigger the questionnaire automation flow for a user.
    This is called after account collection is complete.
    """
    if not mongo_client or not bot_instance:
        print("[Questionnaire] Error: Manager not initialized")
        return

    print(f"[Questionnaire] Triggering questionnaire for user {user_id} in channel {channel_id}")

    try:
        # Update state to questionnaire step
        await StateManager.update_step(channel_id, "questionnaire", {
            "started": True,
            "start_time": datetime.now(timezone.utc)
        })

        # Send interview selection prompt
        await send_interview_selection_prompt(channel_id, user_id)

    except Exception as e:
        print(f"[Questionnaire] Error triggering questionnaire: {e}")
        import traceback
        traceback.print_exc()


async def send_interview_selection_prompt(channel_id: int, user_id: int) -> None:
    """Send the initial interview type selection prompt"""
    if not bot_instance:
        print("[Questionnaire] Error: Bot instance not available")
        return

    try:
        # Create interview selection components
        components = create_container_component(
            INTERVIEW_SELECTION_TEMPLATE,
            accent_color=BLUE_ACCENT,
            user_id=user_id,
            channel_id=channel_id
        )

        # Send the message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID for potential updates
        await StateManager.store_message_id(
            channel_id,
            "interview_selection",
            str(msg.id)
        )

        print(f"[Questionnaire] Sent interview selection to channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending interview selection: {e}")
        import traceback
        traceback.print_exc()


async def halt_automation(channel_id: int, reason: str, user_id: Optional[int] = None) -> None:
    """
    Halt the automation process for manual takeover.
    Used when a recruiter wants to handle the ticket manually.
    """
    if not mongo_client or not bot_instance:
        return

    await StateManager.halt_automation(channel_id, reason)

    # Log the halt
    if user_id:
        log_channel = await bot_instance.rest.fetch_channel(LOG_CHANNEL_ID)
        await log_channel.send(
            f"🛑 **Automation Halted**\n"
            f"Channel: <#{channel_id}>\n"
            f"User: <@{user_id}>\n"
            f"Reason: {reason}"
        )