# extensions/events/message/ticket_automation/core/state_manager.py
"""
Manages the state of ticket automation.
Handles all database operations related to questionnaire state.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hikari

from utils.mongo import MongoClient

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


class StateManager:
    """Centralized state management for ticket automation"""

    @classmethod
    def initialize(cls, mongo: MongoClient, bot: hikari.GatewayBot):
        """Initialize the state manager"""
        global mongo_client, bot_instance
        mongo_client = mongo
        bot_instance = bot

    @classmethod
    async def get_ticket_state(cls, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get the current ticket state"""
        if not mongo_client:
            return None

        return await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})

    # In extensions/events/message/ticket_automation/core/state_manager.py
    # Add this to the StateManager class:

    @classmethod
    async def update_questionnaire_data(cls, channel_id: int, data: dict) -> None:
        """Update questionnaire data in the ticket automation state."""
        if not mongo_client:
            return

        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"step_data.questionnaire.{k}": v for k, v in data.items()}},
            upsert=True
        )

    @classmethod
    async def add_interaction(cls, channel_id: int, interaction_type: str, data: dict = None) -> bool:
        """Record an interaction in the ticket state"""
        if not mongo_client:
            return False

        try:
            interaction = {
                "type": interaction_type,
                "timestamp": datetime.now(timezone.utc),
                "data": data or {}
            }

            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {"$push": {"interactions": interaction}},
                upsert=True
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error adding interaction: {e}")
            return False

    @classmethod
    async def update_step(cls, channel_id: int, step_name: str, step_data: Dict[str, Any]) -> bool:
        """Update the current automation step"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "automation_state.current_step": step_name,
                        f"step_data.{step_name}": step_data,
                        "automation_state.last_updated": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error updating step: {e}")
            return False

    @classmethod
    async def set_current_question(cls, channel_id: int, question_key: str) -> bool:
        """Set the current question being asked"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.current_question": question_key,
                        "step_data.questionnaire.awaiting_response": True
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error setting current question: {e}")
            return False

    @classmethod
    async def store_response(cls, channel_id: int, question_key: str, response: str) -> bool:
        """Store a user's response to a question"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        f"step_data.questionnaire.responses.{question_key}": response,
                        "step_data.questionnaire.awaiting_response": False
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error storing response: {e}")
            return False

    @classmethod
    async def store_message_id(cls, channel_id: int, message_type: str, message_id: str) -> bool:
        """Store a message ID for later reference"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {"$set": {f"step_data.questionnaire.{message_type}": message_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error storing message ID: {e}")
            return False

    @classmethod
    async def get_message_id(cls, channel_id: int, message_type: str) -> Optional[str]:
        """Get a stored message ID"""
        state = await cls.get_ticket_state(str(channel_id))
        if state:
            return state.get("messages", {}).get(message_type)
        return None

    @classmethod
    async def set_interview_type(cls, channel_id: int, interview_type: str) -> bool:
        """Set the interview type (bot_driven or recruiter)"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.interview_type": interview_type,
                        "step_data.questionnaire.started": True
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error setting interview type: {e}")
            return False

    @classmethod
    async def halt_automation(cls, channel_id: int, reason: str) -> bool:
        """Halt the automation process"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "automation_state.status": "halted",
                        "automation_state.halted_reason": reason,
                        "automation_state.halted_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error halting automation: {e}")
            return False

    @classmethod
    async def resume_automation(cls, channel_id: int) -> bool:
        """Resume a halted automation"""
        if not mongo_client:
            return False

        try:
            result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "automation_state.status": "active",
                        "automation_state.halted_reason": None,
                        "automation_state.halted_at": None
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[StateManager] Error resuming automation: {e}")
            return False

    @classmethod
    async def is_automation_active(cls, channel_id: int) -> bool:
        """Check if automation is active for a channel"""
        state = await cls.get_ticket_state(str(channel_id))
        if state:
            return state.get("automation_state", {}).get("status") == "active"
        return False

    @classmethod
    async def get_user_id(cls, channel_id: int) -> Optional[int]:
        """Get the user ID from ticket state"""
        state = await cls.get_ticket_state(str(channel_id))
        if state:
            # Try multiple locations for user ID
            user_id = (
                    state.get("discord_id") or
                    state.get("ticket_info", {}).get("user_id") or
                    state.get("user_id")
            )

            # Convert to int if stored as string
            if user_id:
                try:
                    return int(user_id)
                except (ValueError, TypeError):
                    pass
        return None


# Add this function at the module level (not inside StateManager class)
async def is_awaiting_text_response(channel_id: int) -> bool:
    """Check if waiting for text input from user"""
    if not mongo_client:
        return False

    state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not state:
        return False

    # Check if we're in questionnaire and awaiting response
    questionnaire = state.get("step_data", {}).get("questionnaire", {})
    if not questionnaire.get("awaiting_response"):
        return False

    # Text-based questions that collect continuous input
    current_question = questionnaire.get("current_question")
    text_questions = ["attack_strategies", "future_clan_expectations"]

    # Also check for collecting flags
    collecting_strategies = questionnaire.get("collecting_strategies", False)
    collecting_expectations = questionnaire.get("collecting_expectations", False)

    return (current_question in text_questions or
            collecting_strategies or
            collecting_expectations)