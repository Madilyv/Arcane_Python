# extensions/events/message/ticket_automation/core/question_flow.py
"""
Manages the flow of questions in the questionnaire.
Handles routing to appropriate handlers based on question type.
"""

import asyncio
from typing import Optional, Dict, Any
import hikari

from utils.mongo import MongoClient
from ..utils.constants import QUESTIONNAIRE_QUESTIONS
from .state_manager import StateManager

# Import specific handlers
from ..handlers import (
    attack_strategies,
    clan_expectations,
    discord_skills,
    age_bracket,
    timezone,
    completion
)

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


class QuestionFlow:
    """Manages the flow and routing of questionnaire questions"""

    # Map question types to their handlers
    QUESTION_HANDLERS = {
        "attack_strategies": attack_strategies.send_attack_strategies,
        "future_clan_expectations": clan_expectations.send_clan_expectations,
        "discord_basic_skills": discord_skills.send_discord_skills_question,
        "discord_basic_skills_2": None,  # Handled by standard flow
        "age_bracket": age_bracket.send_age_bracket_question,
        "timezone": timezone.send_timezone_question,
        "leaders_checking_you_out": None,  # Final message, no handler needed
    }

    @classmethod
    def initialize(cls, mongo: MongoClient, bot: hikari.GatewayBot):
        """Initialize the question flow manager"""
        global mongo_client, bot_instance
        mongo_client = mongo
        bot_instance = bot

        # Initialize all handlers
        attack_strategies.initialize(mongo, bot)
        clan_expectations.initialize(mongo, bot)
        discord_skills.initialize(mongo, bot)
        age_bracket.initialize(mongo, bot)
        timezone.initialize(mongo, bot)
        completion.initialize(mongo, bot)

    @classmethod
    async def send_next_question(cls, channel_id: int, user_id: int, current_question: str) -> None:
        """Send the next question in the flow"""
        next_question = cls.get_next_question(current_question)

        if next_question:
            await cls.send_question(channel_id, user_id, next_question)
        else:
            # No more questions, complete the questionnaire
            await completion.send_completion_message(channel_id, user_id)

    @classmethod
    async def send_question(cls, channel_id: int, user_id: int, question_key: str) -> None:
        """Route to the appropriate question handler"""
        print(f"[QuestionFlow] Sending question: {question_key}")

        # Check if this question has a special handler
        handler = cls.QUESTION_HANDLERS.get(question_key)

        if handler:
            # Use the specific handler
            await handler(channel_id, user_id)
        else:
            # Use the standard question sender
            await cls.send_standard_question(channel_id, user_id, question_key)

    @classmethod
    async def send_standard_question(cls, channel_id: int, user_id: int, question_key: str) -> None:
        """Send a standard text-based question"""
        if not bot_instance:
            return

        question = QUESTIONNAIRE_QUESTIONS.get(question_key)
        if not question:
            print(f"[QuestionFlow] Unknown question key: {question_key}")
            return

        # Import here to avoid circular dependency
        from ..components.builders import create_container_component

        try:
            # Update state
            await StateManager.set_current_question(channel_id, question_key)

            # Create template for the question
            template = {
                "title": question.get("title"),
                "content": question.get("content"),
                "footer": question.get("footer"),
                "gif_url": question.get("gif_url")
            }

            # Create and send the question
            components = create_container_component(
                template,
                user_id=user_id
            )

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

            print(f"[QuestionFlow] Sent standard question {question_key}")

            # If this is the final question, wait and then send completion
            if question.get("is_final"):
                await asyncio.sleep(10)  # Give user time to read
                await completion.send_completion_message(channel_id, user_id)

        except Exception as e:
            print(f"[QuestionFlow] Error sending standard question: {e}")
            import traceback
            traceback.print_exc()


    @classmethod
    def get_next_question(cls, current_question: str) -> Optional[str]:
        """Get the next question in the flow"""
        question_data = QUESTIONNAIRE_QUESTIONS.get(current_question)
        if question_data:
            return question_data.get("next")
        return None

    @classmethod
    def is_final_question(cls, question_key: str) -> bool:
        """Check if this is the final question"""
        return question_key == "leaders_checking_you_out"

    @classmethod
    def get_question_data(cls, question_key: str) -> Optional[Dict[str, Any]]:
        """Get the question data for a specific key"""
        return QUESTIONNAIRE_QUESTIONS.get(question_key)