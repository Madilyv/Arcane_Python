# extensions/events/message/ticket_automation/fwa/handlers/lazy_cwl.py
"""
Handles Lazy CWL explanation step - explains the Lazy CWL concept.
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
    """Initialize the Lazy CWL handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_lazy_cwl_explanation(channel_id: int, thread_id: int, user_id: int):
    """Send the Lazy CWL explanation and wait for 'Understood' response"""
    if not bot_instance:
        print("[Lazy CWL] Bot not initialized")
        return

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content=f"## {emojis.CWL} **Heard of Lazy CWL?**"),
                Separator(divider=True),
                Text(content=(
                    f"**We do CWL the LAZY WAY!** Here's what that means:\n\n"
                    f"{emojis.red_arrow_right} **15v15 Format Only** - Maximum medals\n"
                    f"{emojis.red_arrow_right} **Heroes can upgrade** - No waiting!\n"
                    f"{emojis.red_arrow_right} **Use ALL attacks** - Even with heroes down\n"
                    f"{emojis.red_arrow_right} **Hit your mirror** - Same position as you\n"
                    f"{emojis.red_arrow_right} **One-star minimum** - Easy requirement\n\n"
                    f"**The Strategy:**\n"
                    f"• Drop heroes (even if upgrading)\n"
                    f"• Use minimal troops\n"
                    f"• Get one star\n"
                    f"• Collect medals\n"
                    f"• Repeat!\n\n"
                    f"**Why Lazy CWL?**\n"
                    f"✅ Maximum medal rewards\n"
                    f"✅ No stress or pressure\n"
                    f"✅ Heroes always upgrading\n"
                    f"✅ Perfect for farmers\n\n"
                    f"_Remember: In our FWA operation, it's **LAZY WAY or NO WAY!**_"
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
                "step_data.fwa.lazy_cwl_sent": True,
                "step_data.fwa.lazy_cwl_sent_at": datetime.now(timezone.utc),
                "step_data.fwa.awaiting_understood_cwl": True
            }
        )

        print(f"[Lazy CWL] Sent explanation to thread {thread_id}")

    except Exception as e:
        print(f"[Lazy CWL] Error sending explanation: {e}")