# extensions/commands/clan/info_hub/helpers.py

from typing import List, Optional
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.emoji import emojis


async def get_clans_by_type(mongo: MongoClient, clan_type: str) -> List[Clan]:
    """Get all clans of a specific type from MongoDB"""
    # Query for clans by type
    clan_data = await mongo.clans.find({"type": clan_type}).to_list(length=None)

    # Convert to Clan objects
    clans = [Clan(data=data) for data in clan_data]

    return clans


def format_th_requirement(th_level: Optional[int], th_attribute: Optional[str]) -> str:
    """Format TH requirement display"""
    if not th_level:
        return "📋 TH Requirement: Not Set"

    # Get the appropriate TH emoji
    th_emoji_name = f"TH{th_level}"
    th_emoji = getattr(emojis, th_emoji_name, "🏛️")

    # Format the requirement text
    base_text = f"{th_emoji} TH{th_level}"

    if th_attribute:
        if th_attribute == "Max":
            return f"{base_text} Max Only"
        elif th_attribute == "Non-Rushed":
            return f"{base_text}+ Non-Rushed"
        elif th_attribute == "Rushed":
            return f"{base_text}+ (Rushed OK)"
        else:
            return f"{base_text}+"
    else:
        return f"{base_text}+"


def get_league_emoji(league_name: str) -> str:
    """Get the appropriate emoji for a league"""
    league_emojis = {
        "Champion League I": "🏆",
        "Champion League II": "🏆",
        "Champion League III": "🏆",
        "Master League I": "⚔️",
        "Master League II": "⚔️",
        "Master League III": "⚔️",
        "Crystal League I": "💎",
        "Crystal League II": "💎",
        "Crystal League III": "💎",
        "Gold League I": "🥇",
        "Gold League II": "🥇",
        "Gold League III": "🥇",
        "Silver League I": "🥈",
        "Silver League II": "🥈",
        "Silver League III": "🥈",
        "Bronze League I": "🥉",
        "Bronze League II": "🥉",
        "Bronze League III": "🥉",
        "Unranked": "🏅"
    }

    return league_emojis.get(league_name, "🏅")


async def get_clans_by_status(mongo: MongoClient, status: str) -> List[Clan]:
    """Get all clans with a specific status from MongoDB"""
    # Query for clans by status
    clan_data = await mongo.clans.find({"status": status}).to_list(length=None)

    # Convert to Clan objects
    clans = [Clan(data=data) for data in clan_data]

    return clans