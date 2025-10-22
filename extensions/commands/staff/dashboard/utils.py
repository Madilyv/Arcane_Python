"""
Staff Dashboard Utilities
Core functions for forum operations, formatters, and permission checks
"""

import hikari
from datetime import datetime, timezone
from typing import Optional
from utils.mongo import MongoClient

# Forum channel ID for staff logs
STAFF_LOG_FORUM_ID = 1034588368174059570

# Leadership roles that can manage staff logs
LEADERSHIP_ROLES = [
    1345174718944383027,  # Family Lead
    1350830317937627136,  # Hand of the King
    1345183673288228935,  # High Steward
    1345184544822657095,  # Discord Chairman
    1345189412291477575,  # Discord Manager
    1345184642608660573,  # Community Chairman
    1065030453041565696,  # Development Chairman
    1345184776172343318,  # Recruitment Chairman
    1345883351139225752,  # Recruitment Manager
    1345189456038068327,  # Community Manager
]


def is_leadership(member: hikari.Member) -> bool:
    """Check if user has leadership permissions"""
    return any(role_id in member.role_ids for role_id in LEADERSHIP_ROLES)


def format_discord_timestamp(dt: datetime, style: str = "F") -> str:
    """
    Format datetime as Discord timestamp for automatic timezone conversion
    Styles: t=short time, T=long time, d=short date, D=long date,
            f=short datetime, F=long datetime, R=relative
    """
    if dt is None:
        return "Unknown"

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to Unix timestamp
    unix_timestamp = int(dt.timestamp())

    return f"<t:{unix_timestamp}:{style}>"


def generate_next_case_id(existing_cases: list) -> str:
    """Generate random alphanumeric case ID in format SC-XXXXX"""
    import random
    import string

    # Generate unique case ID
    while True:
        # Create random 5-character alphanumeric ID
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        case_id = f"SC-{random_chars}"

        # Check if this ID already exists
        if not any(case.get('case_id') == case_id for case in existing_cases):
            return case_id


async def create_staff_log_thread(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    user: hikari.User,
    member: hikari.Member,
    hire_date: datetime,
    team: str,
    position: str,
    created_by: hikari.User
) -> dict:
    """
    Creates forum thread, posts initial embed, saves to database
    Returns the created log document
    """
    from .embeds import build_forum_embed

    # Build initial log data (without forum IDs yet)
    log_data = {
        "user_id": str(user.id),
        "username": str(user),
        "forum_thread_id": "",  # Will be set after thread creation
        "forum_message_id": "",  # Will be set after thread creation
        "join_date": member.joined_at,
        "hire_date": hire_date,
        "employment_status": "Active",
        "current_team": team,
        "current_position": position,
        "additional_positions": [],  # For staff with multiple roles
        "position_history": [{
            "team": team,
            "position": position,
            "date": hire_date,
            "changed_by_id": str(created_by.id),
            "changed_by_name": str(created_by)
        }],
        "admin_changes": [],
        "staff_cases": [],
        "metadata": {
            "created_at": datetime.now(timezone.utc),
            "created_by_id": str(created_by.id),
            "created_by_name": str(created_by),
            "last_updated": datetime.now(timezone.utc)
        }
    }

    # Build components
    components = build_forum_embed(user, log_data)

    # Create forum post with components
    thread = await bot.rest.create_forum_post(
        STAFF_LOG_FORUM_ID,
        f"{user.username} - Staff Log",
        components=components
    )

    # Fetch the starter message to get correct message ID
    # Forum threads always have a starter message
    starter_message = None
    async for message in bot.rest.fetch_messages(thread.id).limit(1):
        starter_message = message
        break

    if not starter_message:
        raise Exception("Failed to fetch forum starter message")

    # Update log_data with forum IDs
    log_data["forum_thread_id"] = str(thread.id)
    log_data["forum_message_id"] = str(starter_message.id)  # Use actual message ID

    # Save to database
    await mongo.staff_logs.insert_one(log_data)

    print(f"[Staff Dashboard] Created log for {user.username} (ID: {user.id})")
    print(f"[Staff Dashboard DEBUG] Thread ID: {thread.id}, Message ID: {starter_message.id}")
    return log_data


async def update_forum_log(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    user_id: str
) -> None:
    """
    Fetches log from DB, rebuilds embed, edits forum message
    Called after every update operation
    """
    from .embeds import build_forum_embed

    # Get log
    log = await mongo.staff_logs.find_one({"user_id": user_id})

    if not log:
        print(f"[Staff Dashboard] No log found for user {user_id}")
        return

    # Fetch user
    try:
        user = await bot.rest.fetch_user(int(user_id))
    except hikari.NotFoundError:
        print(f"[Staff Dashboard] User {user_id} not found")
        return

    # Build embed
    components = build_forum_embed(user, log)

    # Debug logging
    print(f"[Staff Dashboard DEBUG] Updating forum log:")
    print(f"  - User: {user.username} ({user.id})")
    print(f"  - Forum Thread ID: {log['forum_thread_id']}")
    print(f"  - Forum Message ID: {log['forum_message_id']}")
    print(f"  - Components count: {len(components)}")
    print(f"  - Components type: {type(components)}")

    # Update forum message
    try:
        result = await bot.rest.edit_message(
            channel=int(log['forum_thread_id']),
            message=int(log['forum_message_id']),
            content="",  # Clear any text content
            embeds=[],  # Clear old Discord embeds
            components=components
        )
        print(f"[Staff Dashboard] Updated forum log for {user.username}")
        print(f"[Staff Dashboard DEBUG] Edit result type: {type(result)}")
        print(f"[Staff Dashboard DEBUG] Edit result ID: {result.id if hasattr(result, 'id') else 'N/A'}")
    except Exception as e:
        print(f"[Staff Dashboard] Error updating forum log: {e}")
        import traceback
        traceback.print_exc()


async def get_all_staff_logs(mongo: MongoClient) -> list:
    """Get all staff logs from database"""
    logs = await mongo.staff_logs.find({}).to_list(None)
    return logs or []


async def get_staff_log(mongo: MongoClient, user_id: str) -> Optional[dict]:
    """Get specific staff log by user ID"""
    return await mongo.staff_logs.find_one({"user_id": user_id})


def get_status_emoji(status: str) -> str:
    """Get emoji for employment status"""
    status_emojis = {
        "Active": "🟢",
        "On Leave": "🟡",
        "Inactive": "⚪",
        "Terminated": "🔴"
    }
    return status_emojis.get(status, "⚪")


def get_forum_thread_url(guild_id: int, thread_id: str) -> str:
    """Generate Discord URL for forum thread"""
    return f"https://discord.com/channels/{guild_id}/{thread_id}"
