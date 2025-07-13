# utils/ticket_state.py
"""
Utility functions for managing ticket automation state
"""

from datetime import datetime
from typing import Optional, Dict, List

# Define the automation flow
TICKET_STEPS = {
    "awaiting_screenshot": {
        "index": 1,
        "next": "clan_selection",
        "display": "Upload Screenshot"
    },
    "clan_selection": {
        "index": 2,
        "next": "questionnaire",
        "display": "Select Clan Type"
    },
    "questionnaire": {
        "index": 3,
        "next": "review",
        "display": "Answer Questions"
    },
    "review": {
        "index": 4,
        "next": "final_placement",
        "display": "Application Review"
    },
    "final_placement": {
        "index": 5,
        "next": None,
        "display": "Clan Assignment"
    }
}


async def get_ticket_state(mongo_client, channel_id: str) -> Optional[Dict]:
    """Get ticket automation state by channel ID"""
    return await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})


async def create_ticket_state(mongo_client, channel_id: str, user_id: str,
                              ticket_info: Dict, player_info: Dict = None) -> Dict:
    """Create initial ticket automation state"""

    document = {
        "_id": str(channel_id),
        "ticket_info": {
            "channel_id": str(channel_id),
            "thread_id": str(ticket_info.get("thread", "")),
            "user_id": str(user_id),
            "ticket_type": "TEST",  # TODO: Determine from channel name
            "ticket_number": ticket_info.get("number"),
            "created_at": datetime.now(),
            "last_updated": datetime.now()
        },
        "player_info": player_info or {},
        "automation_state": {
            "current_step": "awaiting_screenshot",
            "current_step_index": 1,
            "total_steps": len(TICKET_STEPS),
            "status": "active",  # active, completed, cancelled, expired
            "completed_steps": [
                {
                    "step_name": "ticket_created",
                    "completed_at": datetime.now(),
                    "data": {}
                }
            ]
        },
        "step_data": {
            "screenshot": {
                "uploaded": False,
                "uploaded_at": None,
                "reminder_sent": False,
                "reminder_count": 0,
                "last_reminder_at": None
            },
            "clan_selection": {
                "selected_clan_type": None,
                "selected_at": None
            },
            "questionnaire": {
                "responses": {},
                "completed_at": None
            },
            "final_placement": {
                "assigned_clan": None,
                "assigned_at": None,
                "approved_by": None
            }
        },
        "messages": {},
        "interaction_history": []
    }

    await mongo_client.ticket_automation_state.insert_one(document)
    return document


async def advance_to_next_step(mongo_client, channel_id: str, step_data: Dict = None) -> str:
    """Advance ticket to the next step in the flow"""

    # Get current state
    current_state = await get_ticket_state(mongo_client, channel_id)
    if not current_state:
        raise ValueError(f"No ticket state found for channel {channel_id}")

    current_step = current_state["automation_state"]["current_step"]

    # Get next step
    next_step = TICKET_STEPS.get(current_step, {}).get("next")
    if not next_step:
        # Already at final step
        return current_step

    # Update to next step
    update_data = {
        "$set": {
            "automation_state.current_step": next_step,
            "automation_state.current_step_index": TICKET_STEPS[next_step]["index"],
            "last_updated": datetime.now()
        },
        "$push": {
            "automation_state.completed_steps": {
                "step_name": current_step,
                "completed_at": datetime.now(),
                "data": step_data or {}
            },
            "interaction_history": {
                "timestamp": datetime.now(),
                "action": "step_completed",
                "details": f"Completed {current_step}, moving to {next_step}"
            }
        }
    }

    # Mark as completed if this was the last step
    if not TICKET_STEPS.get(next_step, {}).get("next"):
        update_data["$set"]["automation_state.status"] = "completed"
        update_data["$set"]["automation_state.completed_at"] = datetime.now()

    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        update_data
    )

    return next_step


async def update_step_data(mongo_client, channel_id: str, step_name: str, data: Dict):
    """Update data for a specific step"""

    update_key = f"step_data.{step_name}"
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                update_key: data,
                "last_updated": datetime.now()
            }
        }
    )


async def add_message_id(mongo_client, channel_id: str, message_type: str, message_id: str):
    """Store a message ID for later reference"""

    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                f"messages.{message_type}": str(message_id),
                "last_updated": datetime.now()
            }
        }
    )


async def add_interaction(mongo_client, channel_id: str, action: str, details: str):
    """Add an interaction to the history"""

    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(),
                    "action": action,
                    "details": details
                }
            },
            "$set": {
                "last_updated": datetime.now()
            }
        }
    )


async def get_active_tickets(mongo_client, step_filter: str = None) -> List[Dict]:
    """Get all active tickets, optionally filtered by step"""

    query = {"automation_state.status": "active"}
    if step_filter:
        query["automation_state.current_step"] = step_filter

    return await mongo_client.ticket_automation_state.find(query).to_list(length=None)


async def close_ticket(mongo_client, channel_id: str, reason: str = "completed"):
    """Mark a ticket as closed"""

    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "automation_state.status": "closed",
                "automation_state.closed_at": datetime.now(),
                "automation_state.close_reason": reason,
                "last_updated": datetime.now()
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(),
                    "action": "ticket_closed",
                    "details": f"Ticket closed: {reason}"
                }
            }
        }
    )


async def is_user_in_active_ticket(mongo_client, user_id: str) -> Optional[str]:
    """Check if a user has an active ticket, return channel_id if found"""

    active_ticket = await mongo_client.ticket_automation_state.find_one({
        "ticket_info.user_id": str(user_id),
        "automation_state.status": "active"
    })

    return active_ticket["_id"] if active_ticket else None