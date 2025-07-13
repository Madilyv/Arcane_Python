# utils/ticket_state.py

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class TicketStep(Enum):
    """Enum for ticket automation steps"""
    AWAITING_SCREENSHOT = "awaiting_screenshot"
    ACCOUNT_COLLECTION = "account_collection"
    QUESTIONNAIRE = "questionnaire"
    CLAN_SELECTION = "clan_selection"
    REVIEW = "review"
    FINAL_PLACEMENT = "final_placement"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TicketState:
    """Manages ticket automation state"""

    STEP_ORDER = [
        TicketStep.AWAITING_SCREENSHOT,
        TicketStep.ACCOUNT_COLLECTION,
        TicketStep.QUESTIONNAIRE,
        TicketStep.CLAN_SELECTION,
        TicketStep.REVIEW,
        TicketStep.FINAL_PLACEMENT,
        TicketStep.COMPLETED
    ]

    @staticmethod
    def get_next_step(current_step: str) -> Optional[str]:
        """Get the next step in the automation flow"""
        try:
            current = TicketStep(current_step)
            current_index = TicketState.STEP_ORDER.index(current)

            if current_index < len(TicketState.STEP_ORDER) - 1:
                return TicketState.STEP_ORDER[current_index + 1].value
            return None
        except (ValueError, IndexError):
            return None

    @staticmethod
    def create_initial_state(
            channel_id: int,
            thread_id: int,
            user_id: int,
            ticket_type: str,
            ticket_number: int,
            user_tag: Optional[str] = None,
            player_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create initial ticket automation state document"""
        return {
            "_id": str(channel_id),
            "ticket_info": {
                "channel_id": channel_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "user_tag": user_tag,
                "player_name": player_name,
                "ticket_type": ticket_type,
                "ticket_number": ticket_number,
                "created_at": datetime.now(timezone.utc)
            },
            "automation_state": {
                "current_step": TicketStep.AWAITING_SCREENSHOT.value,
                "status": "active",
                "completed_steps": []
            },
            "step_data": {
                "screenshot": {
                    "uploaded": False,
                    "reminder_sent": False,
                    "reminder_count": 0,
                    "last_reminder": None
                },
                "account_collection": {
                    "started": False,
                    "completed": False,
                    "additional_accounts": []
                },
                "questionnaire": {
                    "started": False,
                    "completed": False,
                    "responses": {}
                },
                "clan_selection": {
                    "started": False,
                    "completed": False,
                    "selected_clan": None
                }
            },
            "messages": {
                "screenshot_reminder": None,
                "account_collection": None,
                "questionnaire": None,
                "clan_selection": None
            },
            "interaction_history": []
        }

    @staticmethod
    def update_step_completion(
            state: Dict[str, Any],
            step: str,
            data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update state when a step is completed"""
        update = {
            "$set": {
                f"step_data.{step}.completed": True,
                f"step_data.{step}.completed_at": datetime.now(timezone.utc)
            },
            "$addToSet": {
                "automation_state.completed_steps": step
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": f"{step}_completed",
                    "details": data or {}
                }
            }
        }

        # Move to next step
        next_step = TicketState.get_next_step(state["automation_state"]["current_step"])
        if next_step:
            update["$set"]["automation_state.current_step"] = next_step

        return update