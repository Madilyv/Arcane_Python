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
state_manager: Optional[StateManager] = None
loader = lightbulb.Loader()


# Initialize on module load using bot_data
def _initialize_from_bot_data():
    """Initialize using bot_data if available."""
    global mongo_client, bot_instance, state_manager

    if "mongo" in bot_data.data:
        mongo_client = bot_data.data["mongo"]
    if "bot" in bot_data.data:
        bot_instance = bot_data.data["bot"]

    if mongo_client and bot_instance:
        StateManager.initialize(mongo_client, bot_instance)
        # Initialize all handlers
        init_automation(mongo_client, bot_instance)


@loader.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent):
    """Initialize on bot startup."""
    _initialize_from_bot_data()
    print("[Message Events] Ticket automation initialized")


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for questionnaire responses in ticket channels."""

    # Initialize if not already done
    if not state_manager:
        _initialize_from_bot_data()

    if not mongo_client or not bot_instance or not state_manager:
        return

    # Skip bot messages unless checking for Friend Time bot
    if event.is_bot:
        # Check for Friend Time bot confirmation
        if await timezone_handler.check_friend_time_confirmation(event):
            return
        # Skip other bot messages
        return

    # Get ticket state
    ticket_state = await state_manager.get_ticket_state(event.channel_id)
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

    # Check if we're awaiting text response
    if not await is_awaiting_text_response(event.channel_id):
        # Might be waiting for reactions/mentions for discord skills
        if current_question == "discord_skills":
            # These are handled by reaction/mention events
            pass
        return

    # Validate user
    expected_user = await state_manager.get_user_id(event.channel_id)
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

    if not state_manager:
        return

    # Check if this is for a discord skills message
    await discord_skills_handler.check_reaction_completion(
        event.channel_id,
        event.message_id,
        event.user_id,
        str(event.emoji_name)
    )


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_discord_skills_mention(event: hikari.GuildMessageCreateEvent):
    """Handle mentions for Discord skills verification."""

    if event.is_bot:
        return

    if not state_manager or not bot_instance:
        return

    # Check for bot mention
    if bot_instance.get_me() and bot_instance.get_me().id in event.message.user_mentions_ids:
        await discord_skills_handler.check_mention_completion(event.channel_id, event.author_id)


# Re-export loader for use in main.py extensions
__all__ = ['loader']