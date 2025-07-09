# commands/clan/report/helpers.py
"""Shared utilities for report system"""
import re
from typing import Optional, Dict, List
from datetime import datetime

import hikari
from hikari.impl import SelectOptionBuilder as SelectOption

from utils.mongo import MongoClient
from utils.classes import Clan

# Channel Configuration
APPROVAL_CHANNEL = 1350318721771634699
LOG_CHANNEL = 1350340719918936135

# Discord message link regex
DISCORD_LINK_REGEX = re.compile(
    r'https?://(?:www\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)'
)


async def get_clan_options(mongo: MongoClient) -> List[SelectOption]:
    """Get list of clan options for select menu"""
    clan_data = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=d) for d in clan_data]

    options = []
    for c in clans:
        kwargs = {"label": c.name, "value": c.tag, "description": c.tag}
        if getattr(c, "partial_emoji", None):
            kwargs["emoji"] = c.partial_emoji
        options.append(SelectOption(**kwargs))

    return options


def create_progress_header(current: int, total: int, steps: List[str]) -> str:
    """Create a progress indicator for multi-step flows"""
    parts = []
    for i, step in enumerate(steps, 1):
        if i < current:
            parts.append(f"✅ ~~{step}~~")
        elif i == current:
            parts.append(f"🔵 **{step}**")
        else:
            parts.append(f"⚪ {step}")

    return f"**Step {current}/{total}:** " + " → ".join(parts)


def parse_discord_link(link: str) -> Optional[Dict[str, int]]:
    """Parse a Discord message link into its components"""
    match = DISCORD_LINK_REGEX.match(link.strip())
    if match:
        return {
            "guild_id": int(match.group(1)),
            "channel_id": int(match.group(2)),
            "message_id": int(match.group(3))
        }
    return None


async def create_submission_data(
        submission_type: str,
        clan: Clan,
        user: hikari.User,
        **kwargs
) -> dict:
    """Create standardized submission data for approval messages"""
    return {
        "submission_type": submission_type,
        "clan_name": clan.name,
        "clan_tag": clan.tag,
        "clan_logo": clan.logo if clan.logo else "https://cdn-icons-png.flaticon.com/512/845/845665.png",
        "user_id": user.id,
        "user_mention": f"<@{user.id}>",
        "timestamp": int(datetime.now().timestamp()),
        **kwargs  # Additional fields like discord_link, screenshot_url, etc.
    }


def validate_discord_id(discord_id: str) -> bool:
    """Validate a Discord user ID"""
    try:
        # Discord IDs are 17-19 digit numbers
        id_int = int(discord_id)
        return 10 ** 16 <= id_int < 10 ** 19
    except ValueError:
        return False


async def get_clan_by_tag(mongo: MongoClient, tag: str) -> Optional[Clan]:
    """Get clan data by tag"""
    clan_data = await mongo.clans.find_one({"tag": tag})
    if clan_data:
        return Clan(data=clan_data)
    return None