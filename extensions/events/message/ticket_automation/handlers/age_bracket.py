# extensions/events/message/ticket_automation/handlers/age_bracket.py
"""
Handles age bracket selection with themed GIF responses.
Provides different responses based on age selection.
"""

import asyncio
from typing import Optional, Dict, Any
import hikari
import lightbulb

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    SectionComponentBuilder as Section,
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.emoji import emojis
from utils.constants import BLUE_ACCENT, GREEN_ACCENT
from ..core.state_manager import StateManager
from ..utils.constants import QUESTIONNAIRE_QUESTIONS, AGE_RESPONSES

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_age_bracket_question(channel_id: int, user_id: int) -> None:
    """Send the age bracket selection question"""

    if not bot_instance or not mongo_client:
        print("[AgeBracket] Error: Bot not initialized")
        return

    try:
        # Update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": "age_bracket",
                    "step_data.questionnaire.awaiting_response": False  # No text response needed
                }
            }
        )

        question = QUESTIONNAIRE_QUESTIONS["age_bracket"]

        # Create components matching old structure exactly
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"<@{user_id}>"),
                    Separator(divider=True),
                    Text(content=question["title"]),
                    Separator(divider=True),
                    Text(content=question["content"]),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**16 & Under** *(Family-Friendly Clan)*"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧒16 & Under",
                            custom_id=f"age_questionnaire:16_under_{channel_id}_{user_id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**17 – 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧑17 – 25",
                            custom_id=f"age_questionnaire:17_25_{channel_id}_{user_id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**Over 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧓Over 25",
                            custom_id=f"age_questionnaire:over_25_{channel_id}_{user_id}",
                        ),
                    ),
                    Text(
                        content="*Don't worry, we're not knocking on your door! Just helps us get to know you better.*"
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        # Send message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await StateManager.store_message_id(
            channel_id,
            f"questionnaire_age_bracket",
            str(msg.id)
        )

        print(f"[AgeBracket] Sent question to channel {channel_id}")

    except Exception as e:
        print(f"[AgeBracket] Error sending question: {e}")
        import traceback
        traceback.print_exc()


@register_action("age_questionnaire", no_return=True)
async def handle_age_bracket_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user selects an age bracket"""

    parts = action_id.split("_")
    bracket = f"{parts[0]}_{parts[1]}"  # e.g. "16_under", "17_25", "over_25"
    channel_id = parts[2]
    user_id = parts[3]

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This button is only for the ticket owner to click.",
            ephemeral=True
        )
        return

    response = AGE_RESPONSES.get(bracket)
    if not response:
        await ctx.respond("❌ Invalid age bracket selection.", ephemeral=True)
        return

    # Store the age bracket in MongoDB
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.responses.age_bracket": bracket,
                "step_data.questionnaire.age_bracket": bracket
            }
        }
    )

    # Create response components
    response_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content=response["title"]),
                Text(content=response["content"]),
                Media(items=[MediaItem(media=response["gif"])]),
                Text(content="-# Age bracket registered successfully!"),
                Media(items=[MediaItem(media="assets/Gold_Footer.png")])
            ]
        )
    ]

    # The interaction is already deferred by component_handler, so just delete and send new
    await ctx.interaction.delete_initial_response()

    channel = await bot_instance.rest.fetch_channel(int(channel_id))
    await channel.send(
        components=response_components,
        user_mentions=True
    )

    # Wait 10 seconds then send timezone question
    await asyncio.sleep(10)

    # Import here to avoid circular import
    from .timezone import send_timezone_question
    await send_timezone_question(int(channel_id), int(user_id))

    print(f"[Questionnaire] User {user_id} selected age bracket: {bracket}")