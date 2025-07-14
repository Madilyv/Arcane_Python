# extensions/events/message/ticket_automation/__init__.py
"""
Ticket automation system for recruitment process.
"""

from typing import Optional
import hikari
from utils.mongo import MongoClient

# Import core functions that need to be exposed
from .core.questionnaire_manager import (
    trigger_questionnaire,
    send_interview_selection_prompt
)

# Global instances for initialization
_mongo_client: Optional[MongoClient] = None
_bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo_client: MongoClient, bot: hikari.GatewayBot):
    """
    Initialize the ticket automation system.

    Args:
        mongo_client: MongoDB client instance
        bot: Hikari bot instance
    """
    global _mongo_client, _bot_instance
    _mongo_client = mongo_client
    _bot_instance = bot

    # Initialize all sub-modules
    from .core import questionnaire_manager, state_manager, question_flow
    from .handlers import (
        interview_selection,
        attack_strategies,
        clan_expectations,
        discord_skills,
        age_bracket,
        timezone,
        completion
    )

    # Initialize core modules
    questionnaire_manager.initialize(mongo_client, bot)
    state_manager_instance = state_manager.StateManager(mongo_client)
    question_flow.initialize(state_manager_instance, bot)

    # Initialize all handlers
    interview_selection.initialize(state_manager_instance, bot)
    attack_strategies.initialize(state_manager_instance, bot)
    clan_expectations.initialize(state_manager_instance, bot)
    discord_skills.initialize(state_manager_instance, bot)
    age_bracket.initialize(state_manager_instance, bot)
    timezone.initialize(state_manager_instance, bot)
    completion.initialize(state_manager_instance, bot)

    print("[Ticket Automation] All modules initialized")


# Export public API
__all__ = [
    'initialize',
    'trigger_questionnaire',
    'send_interview_selection_prompt'
]