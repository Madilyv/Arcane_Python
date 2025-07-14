# extensions/events/message/ticket_automation/handlers/attack_strategies.py
"""
Handles attack strategies question with AI-powered processing.
Continuously processes user input and updates the display in real-time.
"""

import asyncio
from typing import Optional
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.emoji import emojis
from ..core.state_manager import StateManager
from ..ai.processors import process_attack_strategies_with_ai
from ..components.builders import create_attack_strategy_components
from ..utils.constants import QUESTIONNAIRE_QUESTIONS

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_attack_strategies(channel_id: int, user_id: int) -> None:
    """Send the attack strategies question with AI processing"""

    if not mongo_client or not bot_instance:
        print("[AttackStrategies] Error: Not initialized")
        return

    try:
        # Get ticket state
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            print(f"[AttackStrategies] No ticket state found for channel {channel_id}")
            return

        question_key = "attack_strategies"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Set up state for collecting strategies
        update_result = await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.attack_summary": "",  # Initialize summary
                    "step_data.questionnaire.collecting_strategies": True  # Flag for continuous collection
                }
            }
        )

        print(f"[AttackStrategies] Set collecting_strategies=True, modified: {update_result.modified_count}")

        # Create initial components with empty summary and user ping
        components = await create_attack_strategy_components(
            summary="",
            title=question_data["title"],
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

        print(f"[AttackStrategies] Sent question to channel {channel_id}, msg_id: {msg.id}")

    except Exception as e:
        print(f"[AttackStrategies] Error sending question: {e}")
        import traceback
        traceback.print_exc()


async def process_user_input(channel_id: int, user_id: int, message_content: str) -> None:
    """Process user input for attack strategies"""

    if not mongo_client or not bot_instance:
        return

    try:
        # Get current state
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            return

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

        # Process with AI
        new_summary = await process_attack_strategies_with_ai(current_summary, message_content)

        # Update database with new summary
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.attack_summary": new_summary,
                    "step_data.questionnaire.responses.attack_strategies": new_summary
                }
            }
        )

        # Get message ID and update display
        msg_id = await StateManager.get_message_id(channel_id, "questionnaire_attack_strategies")
        if msg_id:
            try:
                components = await create_attack_strategy_components(
                    new_summary,
                    QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
                    include_user_ping=False  # No ping on updates
                )
                await bot_instance.rest.edit_message(
                    channel_id,
                    int(msg_id),
                    components=components
                )
                print(f"[AttackStrategies] Updated display for channel {channel_id}")
            except Exception as e:
                print(f"[AttackStrategies] Error updating message: {e}")

    except Exception as e:
        print(f"[AttackStrategies] Error processing input: {e}")
        import traceback
        traceback.print_exc()


@register_action("attack_strategies_done", no_return=True)
async def handle_attack_strategies_done(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user clicks Done on attack strategies"""

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

    # Stop collecting strategies
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.collecting_strategies": False,
                "step_data.questionnaire.awaiting_response": False
            }
        }
    )

    # Get the current attack summary to display
    current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

    # Create final components without Done button and without ping
    final_components = await create_attack_strategy_components(
        current_summary,
        QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
        show_done_button=False,
        include_user_ping=False
    )

    # Update the message to remove the Done button
    await ctx.interaction.edit_initial_response(components=final_components)

    # Wait and move to next question
    await asyncio.sleep(2)

    # Move to next question
    next_question = QUESTIONNAIRE_QUESTIONS["attack_strategies"]["next"]
    if next_question:
        await QuestionFlow.send_question(channel_id, user_id, next_question)

    print(f"[AttackStrategies] User {user_id} completed attack strategies")