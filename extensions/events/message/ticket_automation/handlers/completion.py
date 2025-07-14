# extensions/events/message/ticket_automation/handlers/completion.py
"""
Handles questionnaire completion.
Sends final messages and updates automation state.
"""

from datetime import datetime, timezone
from typing import Optional
import hikari

from utils.mongo import MongoClient
from utils.constants import GREEN_ACCENT
from ..core.state_manager import StateManager
from ..components.builders import create_container_component
from ..utils.constants import QUESTIONNAIRE_QUESTIONS

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_completion_message(channel_id: int, user_id: int) -> None:
    """Send the final completion message"""

    if not mongo_client or not bot_instance:
        print("[Completion] Error: Not initialized")
        return

    try:
        # Send the final "leaders checking you out" message first
        await send_leaders_message(channel_id, user_id)

        # Then send the completion message
        completion_template = {
            "title": "🎉 **Questionnaire Complete!**",
            "content": (
                "Thank you for completing the recruitment questionnaire!\n\n"
                "Our team will review your responses and match you with the perfect clan.\n\n"
                "*You'll hear from us soon!*"
            ),
            "footer": None
        }

        components = create_container_component(
            completion_template,
            accent_color=GREEN_ACCENT
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(
            components=components,
            user_mentions=True
        )

        # Update automation state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.completed": True,
                    "step_data.questionnaire.completed_at": datetime.now(timezone.utc),
                    "automation_state.current_step": "clan_selection"
                }
            }
        )

        print(f"[Completion] Questionnaire completed for user {user_id} in channel {channel_id}")

        # TODO: Trigger next automation step (clan selection)
        # This would be implemented when clan selection automation is built

    except Exception as e:
        print(f"[Completion] Error sending completion message: {e}")
        import traceback
        traceback.print_exc()


async def send_leaders_message(channel_id: int, user_id: int) -> None:
    """Send the 'leaders checking you out' message"""

    if not bot_instance:
        return

    try:
        question_data = QUESTIONNAIRE_QUESTIONS.get("leaders_checking_you_out", {})

        template = {
            "title": question_data.get("title", "## 👀 **Clan Leaders are Checking You Out!**"),
            "content": question_data.get("content", "Your application is being reviewed by our clan leaders."),
            "gif_url": question_data.get("gif_url"),
            "footer": None
        }

        components = create_container_component(
            template,
            accent_color=GREEN_ACCENT,
            user_id=user_id
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(
            components=components,
            user_mentions=True
        )

        # Store this as a response
        await StateManager.store_response(channel_id, "leaders_checking_you_out", "viewed")

    except Exception as e:
        print(f"[Completion] Error sending leaders message: {e}")