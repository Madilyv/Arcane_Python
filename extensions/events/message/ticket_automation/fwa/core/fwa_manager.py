# extensions/events/message/ticket_automation/fwa/core/fwa_manager.py
"""
Main FWA automation manager that orchestrates the FWA recruitment flow.
Integrates with existing ticket automation system.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hikari

from utils.mongo import MongoClient
from utils.constants import GREEN_ACCENT, GOLD_ACCENT
from ...core.state_manager import StateManager
from ...components.builders import create_container_component
from ..utils.fwa_constants import FWA_TICKET_PATTERN, FWA_STEPS
from ..utils.chocolate_utils import generate_chocolate_link
from .fwa_flow import FWAFlow, FWAStep

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize_fwa(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the FWA automation system"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot

    # Initialize FWA flow
    FWAFlow.initialize(mongo, bot)

    # Initialize all FWA handlers
    from ..handlers import (
        war_weight,
        fwa_explanation,
        lazy_cwl,
        agreement,
        completion
    )

    war_weight.initialize(mongo, bot)
    fwa_explanation.initialize(mongo, bot)
    lazy_cwl.initialize(mongo, bot)
    agreement.initialize(mongo, bot)
    completion.initialize(mongo, bot)


def is_fwa_ticket(channel_name: str) -> bool:
    """Check if a channel is an FWA ticket"""
    return FWA_TICKET_PATTERN in channel_name or "𝕋-𝔽𝕎𝔸" in channel_name  # Include test pattern


async def trigger_fwa_automation(
        channel_id: int,
        thread_id: int,
        user_id: int,
        ticket_info: Dict[str, Any]
) -> bool:
    """
    Trigger FWA automation flow after screenshot upload.
    This is called from ticket_screenshot.py for FWA tickets.
    """
    if not mongo_client or not bot_instance:
        print("[FWA Manager] Not initialized")
        return False

    try:
        # Get user tag from ticket info
        user_tag = ticket_info.get("user_tag")
        if not user_tag:
            print(f"[FWA Manager] No user tag found for channel {channel_id}")
            return False

        # Send chocolate clash link immediately
        chocolate_url = generate_chocolate_link(user_tag, is_player=True)

        link_components = [
            {
                "type": hikari.ComponentType.ACTION_ROW,
                "components": [{
                    "type": hikari.ComponentType.LINK_BUTTON,
                    "url": chocolate_url,
                    "label": "View FWA Status"
                }]
            }
        ]

        # Send to thread
        await bot_instance.rest.create_message(
            channel=thread_id,
            content=f"🍫 **FWA Chocolate Clash Link:**\n{chocolate_url}",
            component=link_components
        )

        # Update state to FWA war weight collection
        await StateManager.update_ticket_state(
            str(channel_id),
            {
                "automation_state.current_step": "fwa_war_weight",
                "step_data.fwa": {
                    "started": True,
                    "chocolate_link_sent": True,
                    "current_fwa_step": FWAStep.WAR_WEIGHT.value
                }
            }
        )

        # Start FWA flow with war weight request
        await FWAFlow.start_fwa_flow(channel_id, thread_id, user_id)

        print(f"[FWA Manager] Successfully triggered FWA automation for channel {channel_id}")
        return True

    except Exception as e:
        print(f"[FWA Manager] Error triggering automation: {e}")
        import traceback
        traceback.print_exc()
        return False


async def handle_fwa_text_response(
        event: hikari.GuildMessageCreateEvent,
        ticket_state: Dict[str, Any]
) -> bool:
    """
    Handle text responses for FWA flow (Understood, I agree, etc.)
    Returns True if message was handled, False otherwise.
    """
    if not mongo_client or not bot_instance:
        print("[FWA Manager] Not initialized")
        return False

    # Check if we're in FWA flow
    fwa_data = ticket_state.get("step_data", {}).get("fwa", {})
    print(f"[FWA Manager] FWA data: {fwa_data}")  # DEBUG

    if not fwa_data or not fwa_data.get("started"):
        print(f"[FWA Manager] FWA not started or no data")  # DEBUG
        return False

    current_step = fwa_data.get("current_fwa_step")
    print(f"[FWA Manager] Current FWA step: {current_step}")  # DEBUG

    if not current_step:
        print("[FWA Manager] No current FWA step")  # DEBUG
        return False

    # Route to appropriate handler based on current step
    message_content = event.message.content.strip().lower()
    print(f"[FWA Manager] Message content: '{message_content}'")  # DEBUG

    try:
        step_enum = FWAStep(current_step)
        print(f"[FWA Manager] Step enum: {step_enum}")  # DEBUG

        if step_enum == FWAStep.FWA_EXPLANATION:
            if message_content == "understood":
                print("[FWA Manager] Processing 'understood' for FWA_EXPLANATION")  # DEBUG
                await FWAFlow.proceed_to_next_step(
                    int(event.channel_id),
                    int(ticket_state["ticket_info"]["thread_id"]),
                    int(ticket_state["ticket_info"]["user_id"]),
                    FWAStep.LAZY_CWL
                )
                return True

        elif step_enum == FWAStep.LAZY_CWL:
            if message_content == "understood":
                print("[FWA Manager] Processing 'understood' for LAZY_CWL")  # DEBUG
                await FWAFlow.proceed_to_next_step(
                    int(event.channel_id),
                    int(ticket_state["ticket_info"]["thread_id"]),
                    int(ticket_state["ticket_info"]["user_id"]),
                    FWAStep.AGREEMENT
                )
                return True

        elif step_enum == FWAStep.AGREEMENT:
            if message_content == "i agree":
                print("[FWA Manager] Processing 'i agree' for AGREEMENT")  # DEBUG
                await FWAFlow.proceed_to_next_step(
                    int(event.channel_id),
                    int(ticket_state["ticket_info"]["thread_id"]),
                    int(ticket_state["ticket_info"]["user_id"]),
                    FWAStep.COMPLETION
                )
                return True

    except Exception as e:
        print(f"[FWA Manager] Error handling text response: {e}")
        import traceback
        traceback.print_exc()

    return False