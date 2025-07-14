# extensions/events/message/ticket_automation/handlers/interview_selection.py
"""
Handles the initial interview type selection (Bot-driven vs Recruiter).
This determines the path of the questionnaire automation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.constants import GREEN_ACCENT, RED_ACCENT
from ..core.state_manager import StateManager
from ..core.question_flow import QuestionFlow
from ..components.builders import create_container_component
from ..utils.constants import RECRUITMENT_STAFF_ROLE, LOG_CHANNEL_ID

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


@register_action("bot_interview_select", no_return=True)
async def handle_bot_interview_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user selects bot-driven interview"""

    # Extract channel and user IDs from action_id
    parts = action_id.split("_")
    if len(parts) >= 4:
        channel_id = parts[2]
        user_id = parts[3]
    else:
        await ctx.respond("❌ Invalid button data.", ephemeral=True)
        return

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This button is only for the ticket owner to click.",
            ephemeral=True
        )
        return

    # Update the message to show selection
    confirmation_template = {
        "title": "✅ **Bot-Driven Interview Selected!**",
        "content": (
            "Great choice! I'll guide you through the recruitment process step by step.\n"
            "Let's start with understanding your attack strategies..."
        ),
        "footer": None
    }

    confirmation_components = create_container_component(
        confirmation_template,
        accent_color=GREEN_ACCENT
    )

    await ctx.interaction.edit_initial_response(components=confirmation_components)

    # Update database
    await StateManager.set_interview_type(int(channel_id), "bot_driven")

    # Log the interaction
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "selected_bot_interview",
                    "details": {"user_id": user_id}
                }
            }
        }
    )

    # Wait a moment before starting questions
    await asyncio.sleep(2)

    # Send first question (attack strategies)
    await QuestionFlow.send_question(int(channel_id), int(user_id), "attack_strategies")


@register_action("recruiter_interview_select", no_return=True)
async def handle_recruiter_interview_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user selects recruiter interview"""

    # Extract channel and user IDs
    parts = action_id.split("_")
    if len(parts) >= 4:
        channel_id = parts[2]
        user_id = parts[3]
    else:
        await ctx.respond("❌ Invalid button data.", ephemeral=True)
        return

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This button is only for the ticket owner to click.",
            ephemeral=True
        )
        return

    # Update the message to show selection
    confirmation_template = {
        "title": "✅ **Live Recruiter Interview Selected!**",
        "content": (
            f"Great! A member of our recruitment team will be with you shortly.\n\n"
            f"**What happens next:**\n"
            f"• A recruiter will be notified\n"
            f"• They'll join this ticket to conduct your interview\n"
            f"• The interview typically takes 10-15 minutes\n\n"
            f"_Please wait here for a recruiter to arrive!_"
        ),
        "footer": "A recruiter has been notified"
    }

    confirmation_components = create_container_component(
        confirmation_template,
        accent_color=GREEN_ACCENT
    )

    await ctx.interaction.edit_initial_response(components=confirmation_components)

    # Update database
    await StateManager.set_interview_type(int(channel_id), "recruiter")

    # Log the interaction
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "selected_recruiter_interview",
                    "details": {"user_id": user_id}
                }
            }
        }
    )

    # Send notification to recruitment staff
    await notify_recruitment_staff(int(channel_id), int(user_id))

    # Halt automation for manual takeover
    from ..core.questionnaire_manager import halt_automation
    await halt_automation(
        int(channel_id),
        "User selected recruiter interview",
        int(user_id)
    )


async def notify_recruitment_staff(channel_id: int, user_id: int) -> None:
    """Send notification to recruitment staff about manual interview request"""
    if not bot_instance or not LOG_CHANNEL_ID:
        return

    try:
        log_channel = await bot_instance.rest.fetch_channel(LOG_CHANNEL_ID)

        # Get user info
        user = await bot_instance.rest.fetch_user(user_id)

        notification_template = {
            "title": "🎯 **Recruiter Interview Requested**",
            "content": (
                f"**User:** {user.mention} ({user.username})\n"
                f"**Channel:** <#{channel_id}>\n\n"
                f"<@&{RECRUITMENT_STAFF_ROLE}> A user has requested a live interview!"
            ),
            "footer": f"Requested at {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        }

        notification_components = create_container_component(
            notification_template,
            accent_color=RED_ACCENT
        )

        await log_channel.send(
            components=notification_components,
            role_mentions=[RECRUITMENT_STAFF_ROLE]
        )

    except Exception as e:
        print(f"[Interview] Error notifying recruitment staff: {e}")