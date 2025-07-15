# extensions/events/message/ticket_automation/fwa/handlers/completion.py
"""
Handles FWA completion - notifies that FWA leaders are reviewing.
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
from utils.constants import GREEN_ACCENT, GOLD_ACCENT
from utils.emoji import emojis
from ...core.state_manager import StateManager

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None

# Import the existing log channel ID
from ...utils.constants import LOG_CHANNEL_ID


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the completion handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_fwa_completion(channel_id: int, thread_id: int, user_id: int):
    """Send the FWA completion message and update ticket state"""
    if not bot_instance or not mongo_client:
        print("[FWA Completion] Not initialized")
        return

    # Get ticket state for summary
    ticket_state = await StateManager.get_ticket_state(str(channel_id))
    if not ticket_state:
        print(f"[FWA Completion] No ticket state found for channel {channel_id}")
        return

    # Send completion message
    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content=f"## {emojis.FWA} **Application Complete!**"),
                Separator(divider=True),
                Text(content=(
                    "**The FWA Leaders are Reviewing Your Application**\n\n"
                    "Please be patient as this process may take some time. "
                    "Leaders will also need to evaluate roster adjustments to "
                    "accommodate your application.\n\n"
                    "We kindly ask that you **do not ping anyone** during this time. "
                    "Rest assured, we are aware of your presence and will update you "
                    "as soon as possible.\n\n"
                    "_Thank you for your interest in joining our FWA operation!_"
                )),
                Media(items=[MediaItem(media="assets/Gold_Footer.png")])
            ]
        )
    ]

    try:
        await bot_instance.rest.create_message(
            channel=thread_id,
            components=components
        )

        # Update state to completed
        await StateManager.update_ticket_state(
            str(channel_id),
            {
                "automation_state.current_step": "fwa_review",
                "automation_state.status": "completed",
                "step_data.fwa.completed": True,
                "step_data.fwa.completed_at": datetime.now(timezone.utc)
            }
        )

        # Log completion
        await log_fwa_completion(channel_id, thread_id, user_id, ticket_state)

        print(f"[FWA Completion] Process completed for channel {channel_id}")

    except Exception as e:
        print(f"[FWA Completion] Error sending completion: {e}")


async def log_fwa_completion(
        channel_id: int,
        thread_id: int,
        user_id: int,
        ticket_state: dict
):
    """Log FWA completion to the log channel"""
    if not bot_instance:
        return

    ticket_info = ticket_state.get("ticket_info", {})
    fwa_data = ticket_state.get("step_data", {}).get("fwa", {})

    # Create log message
    log_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ✅ **FWA Application Completed**"),
                Separator(divider=True),
                Text(content=(
                    f"**User:** <@{user_id}>\n"
                    f"**Player Tag:** `{ticket_info.get('user_tag', 'Unknown')}`\n"
                    f"**Channel:** <#{channel_id}>\n"
                    f"**Thread:** <#{thread_id}>\n\n"
                    f"**Interview Type:** {ticket_state.get('step_data', {}).get('questionnaire', {}).get('interview_type', 'Unknown')}\n"
                    f"**Additional Accounts:** {len(ticket_state.get('step_data', {}).get('account_collection', {}).get('additional_accounts', []))}\n\n"
                    f"_Application ready for FWA leader review_"
                )),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    try:
        log_channel = bot_instance.cache.get_guild_channel(LOG_CHANNEL_ID)
        if log_channel:
            await bot_instance.rest.create_message(
                channel=log_channel.id,
                components=log_components
            )
    except Exception as e:
        print(f"[FWA Completion] Error logging completion: {e}")