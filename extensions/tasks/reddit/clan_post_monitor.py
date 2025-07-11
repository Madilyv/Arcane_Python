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
DISCORD_CHANNEL_ID = 1345229148880371765
POINTS_CHANNEL_ID = 1345589195695194113
MONITORED_SUBREDDIT = "ClashOfClansRecruit"
SEARCH_KEYWORDS = ["Kings Alliance", "Kings Aliance", "King's Alliance"]  # Handle typos
REDDIT_POST_POINTS = 5

# Debug mode
DEBUG_MODE = os.getenv("CLAN_POST_DEBUG", "False").lower() == "true"


def debug_print(*args, **kwargs):
    """Only print if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[Clan Post Monitor] {args[0]}", *args[1:], **kwargs)


# Global variables
reddit_monitor_task = None
bot_instance = None
mongo_client = None
reddit_instance = None


def extract_clan_tags(text: str) -> List[str]:
    """Extract potential clan tags from text (format: #XXXXXXXXX)"""
    # Match hashtags with 8-9 alphanumeric characters (typical COC clan tag format)
    pattern = r'#[A-Z0-9]{8,9}'
    tags = re.findall(pattern, text.upper())
    debug_print(f"Extracted tags from '{text}': {tags}")
    return tags


async def get_clan_by_tag_from_db(mongo: MongoClient, tag: str) -> Optional[Dict]:
    """Get clan data from MongoDB by tag"""
    # Remove # if present
    clean_tag = tag.replace("#", "")

    # Try with and without hashtag
    clan = await mongo.clans.find_one({"tag": f"#{clean_tag}"})
    if not clan:
        clan = await mongo.clans.find_one({"tag": clean_tag})

    return clan


async def create_points_notification(clan_data: Dict) -> List[Container]:
    """Create the points award notification"""
    clan_name = clan_data.get("name", "Unknown Clan")

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Section(
                    components=[
                        Text(content=f"## {clan_name} +5"),
                        Text(content=(
                            f"• **{clan_name}** was awarded +5 points for posting on Reddit.\n"
                            f"• Clan now has {clan_data.get('points', 0) + 5:.1f} points."
                        )),
                    ],
                    accessory=Thumbnail(
                        media="https://res.cloudinary.com/dxmtzuomk/image/upload/v1752266736/misc_images/Reddit.png")
                ),
            ]
        )
    ]

    return components


async def create_reddit_post_notification(post, clan_data: Dict) -> List[Container]:
    """Create the Discord notification for a Reddit post"""
    # Format the post time
    post_timestamp = int(post.created_utc)

    # Get clan info
    clan_name = clan_data.get("name", "Unknown Clan")
    clan_tag = clan_data.get("tag", "#UNKNOWN")
    banner_url = clan_data.get("banner", None)

    # Build components
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Section(
                    components=[
                        Text(content=f"## 📢 {clan_name} Weekly Reddit Post"),
                        Text(content=(
                            f"{clan_name} has submitted their weekly Reddit post!\n\n"
                            f"**Clan:** {clan_name} ({clan_tag})\n"
                            f"**Posted:** <t:{post_timestamp}:f>\n"
                            f"**Subreddit:** r/{post.subreddit.display_name}\n"
                            f"**Title:** {post.title}\n\n"
                            "Click the button below to check that it meets all posting requirements, "
                            "and don't forget to upvote to show your support!"
                        )),
                    ],
                    accessory=Thumbnail(
                        media="https://res.cloudinary.com/dxmtzuomk/image/upload/v1752266736/misc_images/Reddit.png")
                ),
                Media(items=[MediaItem(media=banner_url if banner_url else "assets/Red_Footer.png")]),
                ActionRow(
                    components=[
                        LinkButton(
                            url=f"https://reddit.com{post.permalink}",
                            label="View Post",
                            emoji="🔗"
                        )
                    ]
                ),
                Text(content=f"-# Posted by u/{post.author.name} on <t:{post_timestamp}:f>")
            ]
        )
    ]

    return components


async def check_reddit_posts():
    """Check Reddit for new posts matching our criteria"""
    global reddit_instance, mongo_client, bot_instance

    if not reddit_instance or not mongo_client or not bot_instance:
        debug_print("Missing required instances")
        return

    try:
        # Get subreddit
        subreddit = await reddit_instance.subreddit(MONITORED_SUBREDDIT)

        # Get recent posts (last 25)
        new_posts = [post async for post in subreddit.new(limit=25)]

        # Get last checked timestamp from MongoDB
        last_check_doc = await mongo_client.reddit_monitor.find_one({"_id": "last_check"})
        last_check_time = last_check_doc.get("timestamp", 0) if last_check_doc else 0

        debug_print(
            f"Checking {len(new_posts)} posts. Last check: {datetime.fromtimestamp(last_check_time) if last_check_time else 'Never'}")

        # Process posts from oldest to newest
        for post in reversed(new_posts):
            # Skip if we've already processed this post
            if post.created_utc <= last_check_time:
                continue

            # Check if title contains our keywords
            title_lower = post.title.lower()
            if any(keyword.lower() in title_lower for keyword in SEARCH_KEYWORDS):
                debug_print(f"Found matching post: {post.title}")

                # Extract clan tags from title
                clan_tags = extract_clan_tags(post.title)

                # Process each clan tag found
                for tag in clan_tags:
                    # Check if clan exists in our database
                    clan_data = await get_clan_by_tag_from_db(mongo_client, tag)

                    if clan_data:
                        debug_print(f"Found clan in database: {clan_data.get('name')} ({tag})")

                        # Check if we've already notified about this post
                        notification_id = f"{post.id}_{tag}"
                        existing_notification = await mongo_client.reddit_notifications.find_one({
                            "_id": notification_id
                        })

                        if not existing_notification:
                            # Create and send notification
                            components = await create_reddit_post_notification(post, clan_data)

                            try:
                                await bot_instance.rest.create_message(
                                    channel=DISCORD_CHANNEL_ID,
                                    components=components
                                )

                                # Award points to the clan
                                current_points = clan_data.get("points", 0)
                                new_points = current_points + REDDIT_POST_POINTS

                                await mongo_client.clans.update_one(
                                    {"tag": tag},
                                    {"$set": {"points": new_points}}
                                )

                                debug_print(
                                    f"Awarded {REDDIT_POST_POINTS} points to {clan_data.get('name')} - Total: {new_points}")

                                # Send points notification
                                points_components = await create_points_notification(clan_data)
                                await bot_instance.rest.create_message(
                                    channel=POINTS_CHANNEL_ID,
                                    components=points_components
                                )

                                # Mark as notified
                                await mongo_client.reddit_notifications.insert_one({
                                    "_id": notification_id,
                                    "post_id": post.id,
                                    "clan_tag": tag,
                                    "points_awarded": REDDIT_POST_POINTS,
                                    "notified_at": datetime.now(timezone.utc).isoformat()
                                })

                                debug_print(f"Sent notification for clan {tag}")
                            except Exception as e:
                                debug_print(f"Error sending notification: {e}")
                    else:
                        debug_print(f"Clan tag {tag} not found in database")

        # Update last check timestamp
        await mongo_client.reddit_monitor.update_one(
            {"_id": "last_check"},
            {"$set": {"timestamp": datetime.now(timezone.utc).timestamp()}},
            upsert=True
        )

    except asyncprawcore.exceptions.ResponseException as e:
        debug_print(f"Reddit API error: {e}")
    except Exception as e:
        debug_print(f"Error checking Reddit: {type(e).__name__}: {e}")


async def reddit_monitor_loop():
    """Main loop that monitors Reddit"""
    debug_print("Starting Reddit monitoring loop...")

    while True:
        try:
            await check_reddit_posts()
            await asyncio.sleep(REDDIT_CHECK_INTERVAL)

        except asyncio.CancelledError:
            debug_print("Monitor loop cancelled")
            break
        except Exception as e:
            debug_print(f"Error in monitor loop: {type(e).__name__}: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


async def initialize_reddit():  # Note: async
    """Initialize Reddit instance with detailed debugging"""
    try:
        # Debug: Check if env vars are loaded
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "KingsAllianceBot/1.0")

        print(f"[REDDIT DEBUG] Client ID: {client_id[:10]}..." if client_id else "[REDDIT DEBUG] Client ID is None!")
        print(f"[REDDIT DEBUG] Secret exists: {bool(client_secret)}")
        print(f"[REDDIT DEBUG] User Agent: {user_agent}")

        # Try to create Reddit instance
        print("[REDDIT DEBUG] Creating Reddit instance...")
        reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        print("[REDDIT DEBUG] Reddit instance created")

        # Test the connection
        print(f"[REDDIT DEBUG] Testing connection to r/{MONITORED_SUBREDDIT}...")
        test_subreddit = await reddit.subreddit(MONITORED_SUBREDDIT)
        subreddit_name = test_subreddit.display_name
        print(f"[REDDIT DEBUG] Successfully connected! Subreddit: {subreddit_name}")

        debug_print("Reddit connection successful")
        return reddit

    except Exception as e:
        print(f"[REDDIT DEBUG] Exception type: {type(e).__name__}")
        print(f"[REDDIT DEBUG] Exception message: {str(e)}")

        # Print full traceback
        import traceback
        print("[REDDIT DEBUG] Full traceback:")
        traceback.print_exc()

        debug_print(f"Failed to initialize Reddit: {type(e).__name__}: {e}")
        return None


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Start the Reddit monitor when bot starts"""
    global reddit_monitor_task, bot_instance, mongo_client, reddit_instance

    # Store instances
    bot_instance = event.app
    mongo_client = mongo

    # Initialize Reddit
    reddit_instance = await initialize_reddit()  # Add await

    if reddit_instance:
        # Start monitoring task
        reddit_monitor_task = asyncio.create_task(reddit_monitor_loop())
        debug_print("Clan Post Monitor task started!")
    else:
        print("[Clan Post Monitor] Failed to initialize Reddit API. Check your credentials.")


@loader.listener(hikari.StoppingEvent)
async def on_bot_stopping(event: hikari.StoppingEvent) -> None:
    """Stop the Reddit monitor when bot stops"""
    global reddit_monitor_task, reddit_instance

    if reddit_monitor_task and not reddit_monitor_task.done():
        reddit_monitor_task.cancel()
        try:
            await reddit_monitor_task
        except asyncio.CancelledError:
            pass
        debug_print("Clan Post Monitor task cancelled")

    # Close Reddit connection
    if reddit_instance:
        await reddit_instance.close()


@loader.command
class ClanPostDebug(
    lightbulb.SlashCommand,
    name="clan-post-debug",
    description="Toggle Clan Post Monitor debug mode",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        global DEBUG_MODE
        DEBUG_MODE = not DEBUG_MODE
        status = "ON" if DEBUG_MODE else "OFF"
        await ctx.respond(f"🔧 Clan Post Monitor debug mode: **{status}**", ephemeral=True)


@loader.command
class ClanPostTest(
    lightbulb.SlashCommand,
    name="clan-post-test",
    description="Manually trigger clan post check",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.defer(ephemeral=True)

        try:
            await check_reddit_posts()
            await ctx.respond("✅ Clan post check completed!")
        except Exception as e:
            await ctx.respond(f"❌ Clan post check failed: {str(e)}")