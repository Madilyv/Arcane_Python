# extensions/events/message/message_events.py
"""
Message event handlers for ticket automation.
"""

import hikari
import lightbulb
from typing import Optional

from utils.mongo import MongoClient
from utils import bot_data

# Import from refactored structure
from .ticket_automation import trigger_questionnaire, initialize as init_automation
from .ticket_automation.core import StateManager
from .ticket_automation.handlers import (
    timezone as timezone_handler,
    attack_strategies as attack_strategies_handler,
    clan_expectations as clan_expectations_handler,
    discord_skills as discord_skills_handler
)
from .ticket_automation.core.state_manager import is_awaiting_text_response

# Global instances - will be initialized from bot_data
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
is_initialized: bool = False  # Track initialization status
loader = lightbulb.Loader()


# Initialize on module load using bot_data
def _initialize_from_bot_data():
    """Initialize using bot_data if available."""
    global mongo_client, bot_instance, is_initialized

    # Check if already initialized
    if is_initialized:
        return

    if "mongo" in bot_data.data:
        mongo_client = bot_data.data["mongo"]
    if "bot" in bot_data.data:
        bot_instance = bot_data.data["bot"]

    if mongo_client and bot_instance:
        StateManager.initialize(mongo_client, bot_instance)
        # Initialize all handlers
        init_automation(mongo_client, bot_instance)
        is_initialized = True  # Mark as initialized


@loader.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent):
    """Initialize on bot startup."""
    _initialize_from_bot_data()
    print("[Message Events] Ticket automation initialized")


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for questionnaire responses in ticket channels."""

    # Initialize if not already done
    if not is_initialized:
        _initialize_from_bot_data()

    if not mongo_client or not bot_instance or not is_initialized:
        return

    # Skip bot messages unless checking for Friend Time bot
    if event.is_bot:
        # Check for Friend Time bot confirmation
        if await timezone_handler.check_friend_time_confirmation(event):
            return
        # Skip other bot messages
        return

    # Get ticket state using StateManager
    ticket_state = await StateManager.get_ticket_state(event.channel_id)
    if not ticket_state:
        return

    # Check if automation is active
    automation_state = ticket_state.get("automation_state", {})
    if automation_state.get("status") != "active":
        return

    # Check if we're in questionnaire step
    if automation_state.get("current_step") != "questionnaire":
        return

    # Get questionnaire data
    questionnaire_data = ticket_state.get("step_data", {}).get("questionnaire", {})
    current_question = questionnaire_data.get("current_question")

    if not current_question:
        return

    # Special handling for discord skills - check ANY message during this question
    if current_question == "discord_basic_skills":
        # Validate user first
        expected_user = await StateManager.get_user_id(event.channel_id)
        if expected_user and event.author_id == expected_user:
            # Check this message for mentions
            await discord_skills_handler.check_mention_completion(
                event.channel_id,
                event.author_id,
                event.message  # Pass the message object
            )
        return

    # Check if we're awaiting text response for other questions
    if not await is_awaiting_text_response(event.channel_id):
        return

    # Validate user
    expected_user = await StateManager.get_user_id(event.channel_id)
    if expected_user and event.author_id != expected_user:
        return

    print(f"[Message Events] Processing response for question: {current_question}")

    # Route to appropriate handler
    if current_question == "attack_strategies":
        await attack_strategies_handler.process_user_input(event.channel_id, event.author_id, event.content)
    elif current_question == "clan_expectations":
        await clan_expectations_handler.process_user_input(event.channel_id, event.author_id, event.content)
    # Other text-based questions are handled by their respective handlers


@loader.listener(hikari.GuildReactionAddEvent)
async def on_discord_skills_reaction(event: hikari.GuildReactionAddEvent):
    """Handle reactions for Discord skills verification."""

    if not is_initialized:
        _initialize_from_bot_data()

    if not is_initialized:
        return

    # Check if this is for a discord skills message
    await discord_skills_handler.check_reaction_completion(
        int(event.channel_id),  # Ensure it's an int
        int(event.message_id),  # Ensure it's an int
        int(event.user_id),  # Ensure it's an int
        str(event.emoji_name)
    )


# Re-export loader for use in main.py extensions
__all__ = ['loader']