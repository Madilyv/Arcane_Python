import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Optional, Dict, List

import hikari
import lightbulb
import asyncpraw
import asyncprawcore

from dotenv import load_dotenv

load_dotenv()

from hikari.impl import (
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    MessageActionRowBuilder as ActionRow,
    LinkButtonBuilder as LinkButton,
    ThumbnailComponentBuilder as Thumbnail,
)

from utils.mongo import MongoClient
from utils.constants import RED_ACCENT

loader = lightbulb.Loader()

# Configuration
REDDIT_CHECK_INTERVAL = 60
DISCORD_CHANNEL_ID = 1345219936297160795  # TH16 recruitment notifications channel
PING_ROLE_ID = 1313898792046559302  # Role to ping for TH16 searches
MONITORED_SUBREDDIT = "ClashOfClansRecruit"

# Debug mode
DEBUG_MODE = os.getenv("TH16_SEARCH_DEBUG", "False").lower() == "true"


def debug_print(*args, **kwargs):
    """Only print if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[TH16 Search Monitor] {args[0]}", *args[1:], **kwargs)


# Global variables
reddit_monitor_task = None
bot_instance = None
mongo_client = None
reddit_instance = None


def is_searching_post(title: str) -> bool:
    """Check if the post title starts with [Searching] (case insensitive)"""
    title_lower = title.lower().strip()
    return title_lower.startswith("[searching]") or title_lower.startswith("[searching ")


def contains_th16(text: str) -> bool:
    """Check if text contains TH16 or Town Hall 16 (case insensitive, ignoring spaces)"""
    text_lower = text.lower()

    # Check for TH16 (with or without spaces)
    if re.search(r'th\s*16', text_lower):
        return True

    # Check for Town Hall 16 (with flexible spacing)
    if re.search(r'town\s*hall\s*16', text_lower):
        return True

    return False


async def create_th16_search_notification(post) -> List[Container]:
    """Create the Discord notification for a TH16 searching post"""
    # Format the post time
    post_timestamp = int(post.created_utc)

    # Extract any clan tags mentioned in the post
    clan_tags = re.findall(r'#[A-Z0-9]{8,9}', post.title.upper())
    clan_tag_text = f"**Mentioned Tags:** {', '.join(clan_tags)}\n" if clan_tags else ""

    # Build components
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Section(
                    components=[
                        Text(content="## 🔍 TH16 Player Looking for Clan"),
                        Text(content=(
                            f"A TH16 player is searching for a clan to join!\n\n"
                            f"**Title:** {post.title}\n"
                            f"**Author:** u/{post.author.name}\n"
                            f"{clan_tag_text}"
                            f"**Posted:** <t:{post_timestamp}:f>\n\n"
                            "Consider reaching out to this player if your clan needs a TH16!"
                        )),
                    ],
                    accessory=Thumbnail(
                        media="https://res.cloudinary.com/dxmtzuomk/image/upload/v1752266736/misc_images/Reddit.png"
                    )
                ),
                ActionRow(
                    components=[
                        LinkButton(
                            url=f"https://reddit.com{post.permalink}",
                            label="View Post",
                            emoji="🔗"
                        ),
                        LinkButton(
                            url=f"https://reddit.com/message/compose/?to={post.author.name}",
                            label="Message Player",
                            emoji="✉️"
                        )
                    ]
                ),
                Text(content=f"-# Posted by u/{post.author.name} on r/{post.subreddit.display_name}")
            ]
        )
    ]

    return components


async def check_th16_posts():
    """Check Reddit for new TH16 searching posts"""
    global reddit_instance, mongo_client, bot_instance

    if not reddit_instance or not mongo_client or not bot_instance:
        debug_print("Missing required instances")
        return

    try:
        # Get subreddit
        subreddit = await reddit_instance.subreddit(MONITORED_SUBREDDIT)

        # Get recent posts (last 25)
        new_posts = [post async for post in subreddit.new(limit=25)]

        # Get last checked timestamp from MongoDB (using separate collection)
        last_check_doc = await mongo_client.reddit_monitor.find_one({"_id": "th16_last_check"})
        last_check_time = last_check_doc.get("timestamp", 0) if last_check_doc else 0

        debug_print(
            f"Checking {len(new_posts)} posts. Last check: {datetime.fromtimestamp(last_check_time) if last_check_time else 'Never'}"
        )

        # Process posts from oldest to newest
        for post in reversed(new_posts):
            # Skip if we've already processed this post
            if post.created_utc <= last_check_time:
                continue

            # Check if it's a searching post and contains TH16
            if is_searching_post(post.title) and contains_th16(post.title):
                debug_print(f"Found TH16 searching post: {post.title}")

                # Check if we've already notified about this post
                notification_id = f"th16_{post.id}"
                existing_notification = await mongo_client.reddit_notifications.find_one({
                    "_id": notification_id
                })

                if not existing_notification:
                    # Create and send notification
                    components = await create_th16_search_notification(post)

                    try:
                        await bot_instance.rest.create_message(
                            channel=DISCORD_CHANNEL_ID,
                            content=f"<@&{PING_ROLE_ID}>",  # Ping the role
                            components=components
                        )

                        # Mark as notified
                        await mongo_client.reddit_notifications.insert_one({
                            "_id": notification_id,
                            "post_id": post.id,
                            "post_title": post.title,
                            "author": post.author.name,
                            "notified_at": datetime.now(timezone.utc).isoformat()
                        })

                        debug_print(f"Sent notification for TH16 searching post by u/{post.author.name}")
                    except Exception as e:
                        debug_print(f"Error sending notification: {e}")

        # Update last check timestamp
        await mongo_client.reddit_monitor.update_one(
            {"_id": "th16_last_check"},
            {"$set": {"timestamp": datetime.now(timezone.utc).timestamp()}},
            upsert=True
        )

    except asyncprawcore.exceptions.ResponseException as e:
        debug_print(f"Reddit API error: {e}")
    except Exception as e:
        debug_print(f"Error checking Reddit: {type(e).__name__}: {e}")


async def reddit_monitor_loop():
    """Main loop that monitors Reddit for TH16 posts"""
    debug_print("Starting TH16 Reddit monitoring loop...")

    while True:
        try:
            await check_th16_posts()
            await asyncio.sleep(REDDIT_CHECK_INTERVAL)

        except asyncio.CancelledError:
            debug_print("Monitor loop cancelled")
            break
        except Exception as e:
            debug_print(f"Error in monitor loop: {type(e).__name__}: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


async def initialize_reddit():
    """Initialize Reddit instance with detailed debugging"""
    try:
        # Debug: Check if env vars are loaded
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "KingsAllianceBot/1.0")

        print(
            f"[TH16 REDDIT DEBUG] Client ID: {client_id[:10]}..." if client_id else "[TH16 REDDIT DEBUG] Client ID is None!")
        print(f"[TH16 REDDIT DEBUG] Secret exists: {bool(client_secret)}")
        print(f"[TH16 REDDIT DEBUG] User Agent: {user_agent}")

        # Try to create Reddit instance
        print("[TH16 REDDIT DEBUG] Creating Reddit instance...")
        reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        print("[TH16 REDDIT DEBUG] Reddit instance created")

        # Test the connection
        print(f"[TH16 REDDIT DEBUG] Testing connection to r/{MONITORED_SUBREDDIT}...")
        test_subreddit = await reddit.subreddit(MONITORED_SUBREDDIT)
        subreddit_name = test_subreddit.display_name
        print(f"[TH16 REDDIT DEBUG] Successfully connected! Subreddit: {subreddit_name}")

        debug_print("Reddit connection successful")
        return reddit

    except Exception as e:
        print(f"[TH16 REDDIT DEBUG] Exception type: {type(e).__name__}")
        print(f"[TH16 REDDIT DEBUG] Exception message: {str(e)}")

        # Print full traceback
        import traceback
        print("[TH16 REDDIT DEBUG] Full traceback:")
        traceback.print_exc()

        debug_print(f"Failed to initialize Reddit: {type(e).__name__}: {e}")
        return None


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Start the TH16 Reddit monitor when bot starts"""
    global reddit_monitor_task, bot_instance, mongo_client, reddit_instance

    # Store instances
    bot_instance = event.app
    mongo_client = mongo

    # Initialize Reddit
    reddit_instance = await initialize_reddit()

    if reddit_instance:
        # Start monitoring task
        reddit_monitor_task = asyncio.create_task(reddit_monitor_loop())
        debug_print("TH16 Search Monitor task started!")
    else:
        print("[TH16 Search Monitor] Failed to initialize Reddit API. Check your credentials.")


@loader.listener(hikari.StoppingEvent)
async def on_bot_stopping(event: hikari.StoppingEvent) -> None:
    """Stop the TH16 Reddit monitor when bot stops"""
    global reddit_monitor_task, reddit_instance

    if reddit_monitor_task and not reddit_monitor_task.done():
        reddit_monitor_task.cancel()
        try:
            await reddit_monitor_task
        except asyncio.CancelledError:
            pass
        debug_print("TH16 Search Monitor task cancelled")

    # Close Reddit connection
    if reddit_instance:
        await reddit_instance.close()


@loader.command
class TH16SearchDebug(
    lightbulb.SlashCommand,
    name="th16-search-debug",
    description="Toggle TH16 Search Monitor debug mode",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        global DEBUG_MODE
        DEBUG_MODE = not DEBUG_MODE
        status = "ON" if DEBUG_MODE else "OFF"
        await ctx.respond(f"🔧 TH16 Search Monitor debug mode: **{status}**", ephemeral=True)


@loader.command
class TH16SearchTest(
    lightbulb.SlashCommand,
    name="th16-search-test",
    description="Manually trigger TH16 search check",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.defer(ephemeral=True)

        try:
            await check_th16_posts()
            await ctx.respond("✅ TH16 search check completed!")
        except Exception as e:
            await ctx.respond(f"❌ TH16 search check failed: {str(e)}")


@loader.command
class TH16SearchStatus(
    lightbulb.SlashCommand,
    name="th16-search-status",
    description="Check TH16 Search Monitor status",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(self, ctx: lightbulb.Context, mongo: MongoClient = lightbulb.di.INJECTED) -> None:
        await ctx.defer(ephemeral=True)

        status_lines = []

        # Check if monitor is running
        if reddit_monitor_task and not reddit_monitor_task.done():
            status_lines.append("✅ Monitor is running")
        else:
            status_lines.append("❌ Monitor is not running")

        # Check Reddit connection
        if reddit_instance:
            status_lines.append("✅ Reddit connection established")
        else:
            status_lines.append("❌ Reddit connection not established")

        # Check last check time
        last_check_doc = await mongo.reddit_monitor.find_one({"_id": "th16_last_check"})
        if last_check_doc:
            last_check_time = datetime.fromtimestamp(last_check_doc.get("timestamp", 0))
            status_lines.append(f"📅 Last check: <t:{int(last_check_doc.get('timestamp', 0))}:R>")
        else:
            status_lines.append("📅 Last check: Never")

        # Get recent notifications count
        recent_notifications = await mongo.reddit_notifications.count_documents({
            "_id": {"$regex": "^th16_"}
        })
        status_lines.append(f"📊 Total notifications sent: {recent_notifications}")

        await ctx.respond("\n".join(status_lines), ephemeral=True)