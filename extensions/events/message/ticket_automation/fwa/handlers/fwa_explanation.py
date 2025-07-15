# extensions/events/message/ticket_automation/fwa/handlers/fwa_explanation.py
"""
Handles FWA explanation step - explains what FWA is and waits for understanding.
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
    """Initialize the FWA explanation handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_fwa_explanation(channel_id: int, thread_id: int, user_id: int):
    """Send the FWA explanation and wait for 'Understood' response"""
    if not bot_instance:
        print("[FWA Explanation] Bot not initialized")
        return

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content="## 🏰 **What is FWA?**"),
                Separator(divider=True),
                Text(content=(
                    f"**FWA** stands for **Farm War Alliance**, a community within Clash of Clans where "
                    f"clans synchronize to match each other in wars.\n\n"
                    f"{emojis.red_arrow_right} **Primary goal:** Win wars easily for loot\n"
                    f"{emojis.red_arrow_right} **Bases:** Must be FWA-approved (we provide these)\n"
                    f"{emojis.red_arrow_right} **Heroes:** Can be upgrading during war\n"
                    f"{emojis.red_arrow_right} **Attacks:** Specific targets assigned\n"
                    f"{emojis.red_arrow_right} **Outcome:** Predetermined winner/loser\n\n"
                    f"**Benefits:**\n"
                    f"• Easy war loot without effort\n"
                    f"• No pressure to perform\n"
                    f"• Heroes can always upgrade\n"
                    f"• Relaxed war environment\n\n"
                    f"_FWA is perfect for farmers who want war loot without the competitive stress!_"
                )),
                Separator(divider=True),
                Text(content="💡 **To continue, type:** `Understood`"),
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
                "step_data.fwa.fwa_explanation_sent": True,
                "step_data.fwa.fwa_explanation_sent_at": datetime.now(timezone.utc),
                "step_data.fwa.awaiting_understood": True
            }
        )

        print(f"[FWA Explanation] Sent explanation to thread {thread_id}")

    except Exception as e:
        print(f"[FWA Explanation] Error sending explanation: {e}")