# extensions/events/message/ticket_automation/handlers/clan_expectations.py
"""
Handles clan expectations question with AI-powered processing.
Similar to attack strategies but focuses on what users expect from clans.
"""

import asyncio
from typing import Optional
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.emoji import emojis
from ..core.state_manager import StateManager
# REMOVED: from ..core.questionnaire_manager import send_question
from ..ai.processors import process_clan_expectations_with_ai
from ..components.builders import create_clan_expectations_components
from ..utils.constants import QUESTIONNAIRE_QUESTIONS

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_clan_expectations(channel_id: int, user_id: int) -> None:
    """Send the clan expectations question with AI processing"""

    if not mongo_client or not bot_instance:
        print("[ClanExpectations] Error: Not initialized")
        return

    try:
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            print(f"[ClanExpectations] No ticket state found for channel {channel_id}")
            return

        question_key = "future_clan_expectations"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Format the content with emoji placeholders
        content = question_data["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

        # Set up state for collecting expectations
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.expectations_summary": "",  # Initialize summary
                    "step_data.questionnaire.collecting_expectations": True  # Flag for continuous collection
                }
            }
        )

        # Create initial components with empty summary
        components = await create_clan_expectations_components(
            "",
            question_data["title"],
            content,
            include_user_ping=True,
            user_id=user_id,
            channel_id=channel_id
        )

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

        print(f"[ClanExpectations] Sent question to channel {channel_id}, msg_id: {msg.id}")

    except Exception as e:
        print(f"[ClanExpectations] Error sending question: {e}")
        import traceback
        traceback.print_exc()


async def process_user_input(channel_id: int, user_id: int, message_content: str) -> None:
    """Process user input for clan expectations"""

    if not mongo_client or not bot_instance:
        return

    try:
        # Get current state
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            return

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("expectations_summary", "")

        # Process with AI
        new_summary = await process_clan_expectations_with_ai(current_summary, message_content)

        # Update database with new summary
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.expectations_summary": new_summary,
                    "step_data.questionnaire.responses.future_clan_expectations": new_summary
                }
            }
        )

        # Get message ID and update display
        msg_id = await StateManager.get_message_id(channel_id, "questionnaire_future_clan_expectations")
        if msg_id:
            try:
                question_data = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]
                content = question_data["content"].format(
                    red_arrow=str(emojis.red_arrow_right),
                    white_arrow=str(emojis.white_arrow_right),
                    blank=str(emojis.blank)
                )

                components = await create_clan_expectations_components(
                    new_summary,
                    question_data["title"],
                    content,
                    include_user_ping=False,  # No ping on updates
                    channel_id=channel_id,
                    user_id=user_id
                )
                await bot_instance.rest.edit_message(
                    channel_id,
                    int(msg_id),
                    components=components
                )
                print(f"[ClanExpectations] Updated display for channel {channel_id}")
            except Exception as e:
                print(f"[ClanExpectations] Error updating message: {e}")

    except Exception as e:
        print(f"[ClanExpectations] Error processing input: {e}")
        import traceback
        traceback.print_exc()


@register_action("clan_expectations_done", no_return=True)
async def handle_clan_expectations_done(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user clicks Done on clan expectations"""

    channel_id = ctx.channel_id
    user_id = ctx.user.id

    # Verify this is the correct user
    ticket_state = await StateManager.get_ticket_state(str(channel_id))
    if not ticket_state:
        await ctx.respond("❌ Ticket state not found.", ephemeral=True)
        return

    stored_user_id = await StateManager.get_user_id(channel_id)
    if not stored_user_id or user_id != stored_user_id:
        await ctx.respond("❌ You cannot interact with this ticket.", ephemeral=True)
        return

    # Stop collecting expectations
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.collecting_expectations": False,
                "step_data.questionnaire.awaiting_response": False
            }
        }
    )

    # Get the current expectations summary
    current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("expectations_summary", "")

    question_data = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]
    content = question_data["content"].format(
        red_arrow=str(emojis.red_arrow_right),
        white_arrow=str(emojis.white_arrow_right),
        blank=str(emojis.blank)
    )

    # Create final components without Done button
    final_components = await create_clan_expectations_components(
        current_summary,
        question_data["title"],
        content,
        show_done_button=False,
        include_user_ping=False,
        channel_id=channel_id,
        user_id=user_id
    )

    # Update the message
    await ctx.interaction.edit_initial_response(components=final_components)

    # Wait and move to next question
    await asyncio.sleep(2)

    # Move to next question
    next_question = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]["next"]
    if next_question:
        # Lazy import to avoid circular dependency
        from ..core.questionnaire_manager import send_question
        await send_question(channel_id, user_id, next_question)

    print(f"[ClanExpectations] User {user_id} completed clan expectations")