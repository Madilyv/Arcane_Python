# extensions/events/message/ticket_automation/handlers/completion.py
"""
Handles questionnaire completion.
Sends final messages and updates automation state.
"""

from datetime import datetime, timezone
from typing import Optional
import hikari

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from utils.mongo import MongoClient
from utils.constants import GREEN_ACCENT, BLUE_ACCENT
from ..core.state_manager import StateManager
# REMOVED: from ..components.builders import create_container_component
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
    """Send the final completion message including leaders checking you out"""

    if not mongo_client or not bot_instance:
        print("[Completion] Error: Not initialized")
        return

    try:
        # Send the final "leaders checking you out" message
        await send_leaders_message(channel_id, user_id)

        # Update automation state to mark completion
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

        # Format the content with emoji replacements if needed
        content = question_data.get("content", "Your application is being reviewed by our clan leaders.")
        footer = question_data.get("footer",
                                   "You've completed the questionnaire! A recruiter will be with you shortly.")

        # Build components inline
        components_list = []

        # Add user ping
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

        # Add title
        title = question_data.get("title", "## 👑 **Leaders Checking You Out**")
        components_list.append(Text(content=title))

        # Add separator if there's content
        if content:
            components_list.append(Separator(divider=True))
            components_list.append(Text(content=content))

        # Add footer if provided
        if footer:
            components_list.append(Text(content=f"-# {footer}"))

        # Add GIF if provided in question data
        gif_url = question_data.get("gif_url")
        if gif_url:
            components_list.append(Media(items=[MediaItem(media=gif_url)]))
        else:
            # Default to green footer for completion
            components_list.append(Media(items=[MediaItem(media="assets/Green_Footer.png")]))

        # Create container with GREEN_ACCENT to indicate completion
        components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=components_list
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(
            components=components,
            user_mentions=True
        )

        # Store this as a response
        await StateManager.store_response(str(channel_id), "leaders_checking_you_out", "viewed")

        # Store message ID
        await StateManager.store_message_id(
            str(channel_id),
            "questionnaire_leaders_checking_you_out",
            "completed"
        )

        print(f"[Completion] Sent leaders checking you out message")

    except Exception as e:
        print(f"[Completion] Error sending leaders message: {e}")
        import traceback
        traceback.print_exc()