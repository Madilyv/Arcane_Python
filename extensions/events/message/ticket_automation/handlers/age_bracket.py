# extensions/events/message/ticket_automation/handlers/age_bracket.py
"""
Handles age bracket selection with themed GIF responses.
Provides different responses based on age selection.
"""

import asyncio
from typing import Optional, Dict, Any
import hikari
import lightbulb

from hikari.impl import MessageActionRowBuilder as ActionRow
from extensions.components import register_action
from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT, GREEN_ACCENT
from ..core.state_manager import StateManager
from ..components.builders import create_container_component, create_button
from ..utils.constants import QUESTIONNAIRE_QUESTIONS
from .timezone import send_timezone_question

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None

# Age bracket responses with GIFs
AGE_RESPONSES = {
    "16_under": {
        "title": "🎉 **16 & Under Registered!**",
        "content": (
            "Got it! Looking forward to having you join our community!\n\n"
            "*Your age group helps us ensure age-appropriate clan placement.*"
        ),
        "gif_url": "https://media1.tenor.com/m/7aoqflH6CnsAAAAC/minions-happy.gif"
    },
    "17_25": {
        "title": "🎮 **17-25 Squad!**",
        "content": (
            "Perfect! You're in the prime gaming age bracket!\n\n"
            "*Get ready to meet fellow gamers in your age range.*"
        ),
        "gif_url": "https://media1.tenor.com/m/VWE8YF9cZdMAAAAC/boom-mind-blown.gif"
    },
    "over_25": {
        "title": "🍻 **25+ Club!**",
        "content": (
            "Welcome to the experienced players club!\n\n"
            "*We have many mature clans perfect for adult gamers.*"
        ),
        "gif_url": "https://media1.tenor.com/m/qBYJywT-W9gAAAAC/steve-buscemi-30rock.gif"
    }
}


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_age_bracket_question(channel_id: int, user_id: int) -> None:
    """Send the age bracket selection question"""

    if not bot_instance:
        print("[AgeBracket] Error: Bot not initialized")
        return

    try:
        question_key = "age_bracket"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Update state
        await StateManager.set_current_question(channel_id, question_key)

        # Create age bracket buttons
        row = ActionRow()

        # 16 & Under button
        row.add_button(
            create_button(
                style=hikari.ButtonStyle.PRIMARY,
                label="16 & Under",
                custom_id=f"age_questionnaire:16_under_{channel_id}_{user_id}",
                emoji="👶"
            )
        )

        # 17-25 button
        row.add_button(
            create_button(
                style=hikari.ButtonStyle.PRIMARY,
                label="17-25",
                custom_id=f"age_questionnaire:17_25_{channel_id}_{user_id}",
                emoji="🎮"
            )
        )

        # 25+ button
        row.add_button(
            create_button(
                style=hikari.ButtonStyle.PRIMARY,
                label="25+",
                custom_id=f"age_questionnaire:over_25_{channel_id}_{user_id}",
                emoji="🧔"
            )
        )

        # Create message components
        template = {
            "title": question_data["title"],
            "content": question_data["content"],
            "footer": None
        }

        components = create_container_component(
            template,
            accent_color=BLUE_ACCENT,
            user_id=user_id
        )

        # Add button row
        components.append(row)

        # Send message
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

    # Get response data
    response_data = AGE_RESPONSES.get(bracket, AGE_RESPONSES["17_25"])

    # Store the selection
    await StateManager.store_response(int(channel_id), "age_bracket", bracket)

    # Create response with GIF
    response_template = {
        "title": response_data["title"],
        "content": response_data["content"],
        "gif_url": response_data["gif_url"],
        "footer": None
    }

    response_components = create_container_component(
        response_template,
        accent_color=GREEN_ACCENT
    )

    # Delete original message and send new one
    await ctx.interaction.delete_initial_response()

    channel = await bot_instance.rest.fetch_channel(int(channel_id))
    await channel.send(
        components=response_components,
        user_mentions=True
    )

    # Wait then send timezone question
    await asyncio.sleep(10)
    await send_timezone_question(int(channel_id), int(user_id))

    print(f"[AgeBracket] User {user_id} selected age bracket: {bracket}")