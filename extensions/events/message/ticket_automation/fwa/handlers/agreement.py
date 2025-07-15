# extensions/events/message/ticket_automation/fwa/handlers/agreement.py
"""
Handles FWA agreement step - confirms understanding of Lazy CWL commitment.
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
from utils.constants import GOLD_ACCENT
from utils.emoji import emojis
from ...core.state_manager import StateManager

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the agreement handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_agreement_message(channel_id: int, thread_id: int, user_id: int):
    """Send the agreement message with GIF and wait for 'I agree' response"""
    if not bot_instance:
        print("[FWA Agreement] Bot not initialized")
        return

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content="## 🤝 **Final Confirmation**"),
                Separator(divider=True),
                Text(content=(
                    "Do you **truly understand** Lazy CWL and agree that when in our "
                    "FWA operation it is:\n\n"
                    "# **LAZY WAY or NO WAY!**\n\n"
                    "This means:\n"
                    "• You'll use the FWA base we provide\n"
                    "• You'll follow all FWA rules\n"
                    "• You'll participate in Lazy CWL\n"
                    "• You understand the relaxed approach\n\n"
                    "_This is your commitment to the FWA lifestyle!_"
                )),
                Media(
                    items=[
                        MediaItem(media="https://c.tenor.com/-IE-fH9z1CwAAAAd/tenor.gif"),
                    ]
                ),
                Separator(divider=True),
                Text(content="✅ **To continue, type:** `I agree`"),
                Media(items=[MediaItem(media="assets/Gold_Footer.png")])
            ]
        )
    ]

    try:
        await bot_instance.rest.create_message(
            channel=thread_id,
            components=components
        )

        # Update state
        await StateManager.update_ticket_state(
            str(channel_id),
            {
                "step_data.fwa.agreement_sent": True,
                "step_data.fwa.agreement_sent_at": datetime.now(timezone.utc),
                "step_data.fwa.awaiting_agreement": True
            }
        )

        print(f"[FWA Agreement] Sent agreement message to thread {thread_id}")

    except Exception as e:
        print(f"[FWA Agreement] Error sending agreement: {e}")