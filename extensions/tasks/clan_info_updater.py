# extensions/tasks/clan_info_updater.py
"""
Scheduled task to update clan information embeds in threads every 5 minutes.
Fetches clan data from CoC API and updates Components v2 embeds in Discord threads.
"""

import asyncio
import hikari
import lightbulb
import coc
from datetime import datetime, timezone
from typing import Optional, Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    InteractiveButtonBuilder as Button,
    LinkButtonBuilder as LinkButton,
    MessageActionRowBuilder as ActionRow,
    SectionComponentBuilder as Section,
    ThumbnailComponentBuilder as Thumbnail,
)

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT, GREEN_ACCENT
from utils.emoji import emojis
from utils.classes import Clan

loader = lightbulb.Loader()

# Configuration
UPDATE_INTERVAL_MINUTES = 60  # Change this to adjust update frequency
CLAN_INFO_PARENT_CHANNEL = 1133096989748363294  # Clan threads parent channel

# Global instances
mongo_client: Optional[MongoClient] = None
coc_client: Optional[coc.Client] = None
bot_instance: Optional[hikari.GatewayBot] = None
scheduler: Optional[AsyncIOScheduler] = None


async def build_clan_info_embed(clan: Clan, api_clan: coc.Clan, guild_id: int) -> List[Container]:
    """Build the clan information embed"""

    # Get leader from MongoDB
    leader_mention = f"<@{clan.leader_id}>" if clan.leader_id else "@Unknown"

    # Format location
    location = "International" if not api_clan.location else api_clan.location.name

    # Get CWL league emoji
    cwl_emoji = "🏆"
    if hasattr(api_clan, 'war_league') and api_clan.war_league:
        league_name = api_clan.war_league.name
        league_emoji_map = {
            "Champion League I": emojis.Champ1,
            "Champion League II": emojis.Champ2,
            "Champion League III": emojis.Champ3,
            "Master League I": emojis.Master1,
            "Master League II": emojis.Master2,
            "Master League III": emojis.Master3,
            "Crystal League I": emojis.Crystal1,
            "Crystal League II": emojis.Crystal2,
            "Crystal League III": emojis.Crystal3,
            "Gold League I": emojis.Gold1,
            "Gold League II": emojis.Gold2,
            "Gold League III": emojis.Gold3,
            "Silver League I": emojis.Silver1,
            "Silver League II": emojis.Silver2,
            "Silver League III": emojis.Silver3,
        }
        if league_name in league_emoji_map:
            cwl_emoji = f"{league_emoji_map[league_name].partial_emoji}"

    # Get capital hall level - EXACTLY like clan list
    if api_clan and api_clan.capital_districts:
        peak = max(d.hall_level for d in api_clan.capital_districts)
    else:
        peak = 0

    # Get badge URL
    badge_url = None
    if hasattr(api_clan, 'badge') and api_clan.badge:
        badge_url = api_clan.badge.url
    elif clan.logo:
        badge_url = clan.logo

    # Format recruiting - TH emoji + TH number
    recruiting = "N/A"
    if clan.th_requirements:
        th_emoji_name = f"TH{clan.th_requirements}"
        th_emoji = getattr(emojis, th_emoji_name, "🏛️")
        recruiting = f"{th_emoji} TH{clan.th_requirements}"

    # Build components list
    components = []

    # First container - main info with buttons inside
    main_container_components = []

    if badge_url:
        main_container_components.append(
            Section(
                components=[
                    Text(content=(
                        f"# {api_clan.name}\n\n"
                        f"Tag: {api_clan.tag}\n"
                        f"Trophies: 🏆 {api_clan.points:,}\n"
                        f"Required Trophies: 🏆 {api_clan.required_trophies:,}\n"
                        f"Clan Open Status: {api_clan.type if hasattr(api_clan, 'type') else 'unknown'}\n"
                        f"Clan Type: {clan.type or 'Competitive'}\n"
                        f"Location: 🌍 {location}\n\n"
                        f"Leader: {leader_mention}\n"
                        f"Clan Level: {api_clan.level}\n"
                        f"Members: 👥 {api_clan.member_count}/50\n"
                        f"Recruiting: {recruiting}\n\n"
                        f"CWL: {cwl_emoji}{api_clan.war_league.name if hasattr(api_clan, 'war_league') and api_clan.war_league else 'Unranked'}\n"
                        f"Wars Won: ⚔️ {api_clan.war_wins}\n"
                        f"Capital Hall Level: 🏰 {peak}"
                    ))
                ],
                accessory=Thumbnail(media=badge_url)
            )
        )
        main_container_components.append(Separator(divider=True))
        main_container_components.append(
            Text(content=(
                f"## In-Game Description\n"
                f"{api_clan.description or 'No description set.'}"
            ))
        )
    else:
        main_container_components.extend([
            Text(content=(
                f"# {api_clan.name}\n\n"
                f"Tag: {api_clan.tag}\n"
                f"Trophies: 🏆 {api_clan.points:,}\n"
                f"Required Trophies: 🏆 {api_clan.required_trophies:,}\n"
                f"Clan Open Status: {api_clan.type if hasattr(api_clan, 'type') else 'unknown'}\n"
                f"Clan Type: {clan.type or 'Competitive'}\n"
                f"Location: 🌍 {location}\n\n"
                f"Leader: {leader_mention}\n"
                f"Clan Level: {api_clan.level}\n"
                f"Members: 👥 {api_clan.member_count}/50\n"
                f"Recruiting: {recruiting}\n\n"
                f"CWL: {cwl_emoji}{api_clan.war_league.name if hasattr(api_clan, 'war_league') and api_clan.war_league else 'Unranked'}\n"
                f"Wars Won: ⚔️ {api_clan.war_wins}\n"
                f"Capital Hall Level: 🏰 {peak}"
            )),
            Separator(divider=True),
            Text(content=(
                f"## In-Game Description\n"
                f"{api_clan.description or 'No description set.'}"
            ))
        ])

    # Create first container
    components.append(
        Container(
            accent_color=BLUE_ACCENT,
            components=main_container_components
        )
    )

    # Second container - profile section (always shows)
    profile_components = [
        Text(content=f"# {api_clan.name} Profile"),
        Text(content=(
            clan.profile if clan.profile else
            f"{api_clan.name}' future \"About Me\" section is currently in progress, "
            "designed to introduce each clan within Kings Alliance.\n\n"
            "We aim to craft a unique description for each clan to showcase "
            "their distinct character and give you insight into the heart of their "
            "leadership."
        )),
    ]

    # Add banner if exists
    if clan.banner:
        profile_components.append(Media(items=[MediaItem(media=clan.banner)]))

    # Add timestamp
    profile_components.append(Text(content=f"\nAuto Refreshed at • <t:{int(datetime.now().timestamp())}:f>"))

    profile_components.append(Separator(divider=True))

    # Add buttons to main container
    profile_components.append(
        ActionRow(
            components=[
                LinkButton(
                    url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={api_clan.tag.replace('#', '')}",
                    label="Open In-Game",
                    emoji="📱"
                ),
                LinkButton(
                    url=f"https://discord.com/channels/{guild_id}/1133096989748363294",
                    label="Back to Main Clan Info",
                    emoji="🔙"
                )
            ]
        )
    )

    components.append(
        Container(
            accent_color=BLUE_ACCENT,
            components=profile_components
        )
    )

    return components


async def update_clan_threads():
    """Main task to update all clan threads"""
    if not all([mongo_client, coc_client, bot_instance]):
        print("[Clan Info Updater] Missing required clients, skipping update")
        return

    try:
        # Get all clans from database
        clan_data = await mongo_client.clans.find({}).to_list(length=None)

        for clan_doc in clan_data:
            try:
                # Skip if no thread_id
                if not clan_doc.get('thread_id'):
                    continue

                clan = Clan(data=clan_doc)
                thread_id = clan.thread_id

                # Skip if essential data is missing
                if not clan.tag:
                    print(f"[Clan Info Updater] Skipping clan with no tag")
                    continue

                # Get clan data from CoC API
                try:
                    api_clan = await coc_client.get_clan(clan.tag)
                except Exception as e:
                    print(f"[Clan Info Updater] Failed to fetch API data for {clan.tag}: {e}")
                    continue

                # Get guild ID from thread
                try:
                    thread = await bot_instance.rest.fetch_channel(thread_id)
                    guild_id = thread.guild_id
                    if hasattr(thread, 'is_archived') and thread.is_archived:
                        await bot_instance.rest.edit_channel(
                            thread_id,
                            archived=False,
                            auto_archive_duration=10080  # 7 days
                        )
                except Exception as e:
                    print(f"[Clan Info Updater] Failed to check/unarchive thread {thread_id}: {e}")
                    continue

                # Build embed components
                components = await build_clan_info_embed(clan, api_clan, guild_id)

                # Check if we have an existing message
                existing_message_id = clan_doc.get('thread_message_id')

                try:
                    if existing_message_id:
                        # Try to edit existing message
                        await bot_instance.rest.edit_message(
                            channel=thread_id,
                            message=existing_message_id,
                            components=components,
                            user_mentions=False,
                            role_mentions=False
                        )
                        print(f"[Clan Info Updater] Updated message for {clan.name}")
                    else:
                        # Create new message
                        message = await bot_instance.rest.create_message(
                            channel=thread_id,
                            components=components,
                            user_mentions=False,
                            role_mentions=False
                        )

                        # Save message ID to database
                        await mongo_client.clans.update_one(
                            {"tag": clan.tag},
                            {"$set": {"thread_message_id": message.id}}
                        )
                        print(f"[Clan Info Updater] Created new message for {clan.name}")

                except hikari.NotFoundError:
                    # Message was deleted, create a new one
                    message = await bot_instance.rest.create_message(
                        channel=thread_id,
                        components=components,
                        user_mentions=False,
                        role_mentions=False
                    )

                    # Save new message ID
                    await mongo_client.clans.update_one(
                        {"tag": clan.tag},
                        {"$set": {"thread_message_id": message.id}}
                    )
                    print(f"[Clan Info Updater] Recreated message for {clan.name}")

                except Exception as e:
                    print(f"[Clan Info Updater] Failed to update message for {clan.name}: {e}")

                # Small delay to avoid rate limits
                await asyncio.sleep(1)

            except Exception as e:
                print(f"[Clan Info Updater] Error processing clan: {e}")
                continue

        print(f"[Clan Info Updater] Update cycle completed at {datetime.now()}")

    except Exception as e:
        print(f"[Clan Info Updater] Critical error in update task: {e}")


@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent):
    """Initialize the clan info updater when bot starts"""
    global mongo_client, coc_client, bot_instance, scheduler

    # Get instances from bot data
    from utils import bot_data
    mongo_client = bot_data.data.get("mongo")
    coc_client = bot_data.data.get("coc_client")
    bot_instance = bot_data.data.get("bot")

    if not all([mongo_client, coc_client, bot_instance]):
        print("[Clan Info Updater] ERROR: Missing required clients!")
        return

    # Initialize scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Schedule the update task
    scheduler.add_job(
        update_clan_threads,
        trigger=IntervalTrigger(minutes=UPDATE_INTERVAL_MINUTES),
        id="clan_info_updater",
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )

    # Start scheduler
    scheduler.start()

    print(f"[Clan Info Updater] Started - updating every {UPDATE_INTERVAL_MINUTES} minutes")

    # Run initial update after 5 seconds
    await asyncio.sleep(5)
    await update_clan_threads()


@loader.listener(hikari.StoppingEvent)
async def on_stopping(event: hikari.StoppingEvent):
    """Cleanup when bot stops"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("[Clan Info Updater] Scheduler shut down")