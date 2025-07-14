# extensions/events/message/ticket_automation/handlers/interview_selection.py

from typing import Optional
import hikari
import lightbulb
from datetime import datetime, timezone

from extensions.components import register_action
from utils.mongo import MongoClient
from ..core.state_manager import StateManager
from ..core import questionnaire_manager
from ..utils.constants import RECRUITMENT_STAFF_ROLE

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the interview selection handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


@register_action("select_bot_interview", no_return=True)
async def handle_bot_interview_selection(ctx: lightbulb.components.MenuContext, action_id: str, **kwargs):
    """Handle when user selects bot-driven interview"""

    # Extract channel_id and user_id from action_id
    parts = action_id.split("_")
    channel_id = parts[0]
    user_id = parts[1]

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This is not your recruitment process.",
            ephemeral=True
        )
        return

    # Update the state
    await StateManager.update_questionnaire_data(int(channel_id), {
        "interview_type": "bot",
        "started": True
    })

    # Record interaction
    await StateManager.add_interaction(int(channel_id), "selected_bot_interview", {"user_id": user_id})

    # Send first question using questionnaire manager
    await questionnaire_manager.send_question(int(channel_id), int(user_id), "attack_strategies")


@register_action("select_recruiter_interview", no_return=True)
async def handle_recruiter_interview_selection(ctx: lightbulb.components.MenuContext, action_id: str, **kwargs):
    """Handle when user selects recruiter interview"""

    # Extract channel_id and user_id from action_id
    parts = action_id.split("_")
    channel_id = parts[0]
    user_id = parts[1]

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This is not your recruitment process.",
            ephemeral=True
        )
        return

    # Update the state
    await StateManager.update_questionnaire_data(int(channel_id), {
        "interview_type": "recruiter",
        "started": True
    })

    # Halt automation for manual handling
    await StateManager.halt_automation(int(channel_id), "User selected recruiter interview")

    # Notify recruitment staff
    await ctx.respond(
        f"<@&{RECRUITMENT_STAFF_ROLE}> {ctx.user.mention} has requested a live interview!",
        role_mentions=True
    )