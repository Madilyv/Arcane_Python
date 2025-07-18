import aiohttp
import asyncio
import lightbulb
import hikari
from datetime import datetime
import json
import os

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    InteractiveButtonBuilder as Button,
    LinkButtonBuilder as LinkButton,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.constants import RED_ACCENT, GREEN_ACCENT

loader = lightbulb.Loader()

# DEBUG CONFIGURATION - Change this to False for production
DEBUG_MODE = os.getenv("BAND_DEBUG", "False").lower() == "true"  # Set via environment variable


# Alternative: DEBUG_MODE = True  # Set directly

def debug_print(*args, **kwargs):
    """Only print if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(*args, **kwargs)


# BAND API Configuration
BAND_API_BASE = "https://openapi.band.us/v2/band/posts"
BAND_ACCESS_TOKEN = "ZQAAAR-9LGjvTxYmwok2WaTSYvcrA8M84ZK3s5BQSxxmggdJkyIFUUT4KCFvH1QNz2I3syNF_2aKaPLtownMSAVAC7pprIKu1TD_600hDD8GjhvX"
BAND_KEY = "AADMPvOeSi6era-iwqaVkEtP"

# Discord channel to send notifications
NOTIFICATION_CHANNEL_ID = 1078702146180104233
ALLOWED_ROLE_ID = 1088914884999249940

# Global variables
band_check_task = None
bot_instance = None  # Store bot reference for sending messages
mongo_client = None  # Store mongo reference


async def fetch_band_posts():
    """Fetch posts from BAND API"""
    params = {
        "access_token": BAND_ACCESS_TOKEN,
        "band_key": BAND_KEY,
        "locale": "en_US"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BAND_API_BASE, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    debug_print(f"[BAND API] Error: Status {response.status}")
                    text = await response.text()
                    debug_print(f"[BAND API] Response: {text}")
                    return None
        except Exception as e:
            debug_print(f"[BAND API] Exception: {type(e).__name__}: {e}")
            return None


async def send_war_sync_to_discord(post):
    """Send a War Sync reminder to Discord channel using Components V2"""
    global bot_instance

    if not bot_instance:
        debug_print("[BAND Monitor] Bot instance not available!")
        return

    # Extract post details
    author = post.get('author', {})
    author_name = author.get('name', 'FWA Clan Rep')
    content = post.get('content', '')

    # Create message ID for tracking responses
    message_id = str(datetime.now().timestamp())

    # Create components using V2 style
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content="## ⚔️ War Sync Event has been posted."),
                Text(content=f"<@&{ALLOWED_ROLE_ID}> - A new FWA War Sync has been scheduled!"),
                Separator(divider=True),
                ActionRow(
                    components=[
                        LinkButton(
                            url="https://www.band.us/band/57375315",
                            label="Check FWA Sync Time",
                            emoji="🕐"
                        )
                    ]
                ),
                Text(content=(
                    "Please review the **FWA Sync Time** and confirm your availability by selecting the "
                    "corresponding button below:"
                )),
                Separator(divider=True),
                Text(content="✅ - If you are available to start."),
                Text(content="📅 - If you may be available to start."),
                Text(content="❌ - If you are unavailable to start."),
                Separator(divider=True),
                Text(content=(
                    "*Please note that if your availability changes, you can update your response by "
                    "selecting the appropriate button.*"
                )),
                Separator(divider=True),
                Text(content="## Rep Availability"),
                Text(content="*No responses yet...*"),
                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Yes",
                            emoji="✅",
                            custom_id=f"war_response:yes_{message_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Maybe",
                            emoji="📅",
                            custom_id=f"war_response:maybe_{message_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.DANGER,
                            label="No",
                            emoji="❌",
                            custom_id=f"war_response:no_{message_id}"
                        ),
                    ]
                ),
            ]
        )
    ]

    try:
        # Send the message
        message = await bot_instance.rest.create_message(
            channel=NOTIFICATION_CHANNEL_ID,
            components=components,
            user_mentions=True,
            role_mentions=[ALLOWED_ROLE_ID]
        )

        debug_print(f"[BAND Monitor] Sent War Sync reminder to Discord")
    except Exception as e:
        debug_print(f"[BAND Monitor] Failed to send Discord message: {e}")


@register_action("war_response", no_return=True)
@lightbulb.di.with_di
async def on_war_response(
        action_id: str,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle war sync response buttons"""
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]
    response_type, message_id = action_id.split("_", 1)

    # Check if user has the required role
    member = ctx.member
    if not any(role == ALLOWED_ROLE_ID for role in member.role_ids):
        await ctx.respond(
            "❌ You don't have permission to respond to War Sync events.",
            ephemeral=True
        )
        return

    # Get stored data from fwa_band_data collection
    stored_data = await mongo.fwa_band_data.find_one({"_id": message_id})
    if not stored_data:
        stored_data = {"_id": message_id, "responses": {}}
        await mongo.fwa_band_data.insert_one(stored_data)

    # Update user's response
    user_id = str(ctx.user.id)
    old_response = stored_data["responses"].get(user_id)
    stored_data["responses"][user_id] = response_type

    # Save to mongo
    await mongo.fwa_band_data.update_one(
        {"_id": message_id},
        {"$set": {"responses": stored_data["responses"]}}
    )

    # Build response lists
    yes_users = []
    maybe_users = []
    no_users = []

    for uid, resp in stored_data["responses"].items():
        mention = f"<@{uid}>"
        if resp == "yes":
            yes_users.append(mention)
        elif resp == "maybe":
            maybe_users.append(mention)
        elif resp == "no":
            no_users.append(mention)

    # Build response text
    response_lines = []
    if yes_users:
        response_lines.append(f"✅ **Available** - {', '.join(yes_users)}")
    if maybe_users:
        response_lines.append(f"📅 **Maybe** - {', '.join(maybe_users)}")
    if no_users:
        response_lines.append(f"❌ **Unavailable** - {', '.join(no_users)}")

    if not response_lines:
        response_lines.append("*No responses yet...*")

    # Update the message with new responses
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content="## ⚔️ War Sync Event has been posted."),
                Text(content=f"<@&{ALLOWED_ROLE_ID}> - A new FWA War Sync has been scheduled!"),
                Separator(divider=True),
                ActionRow(
                    components=[
                        LinkButton(
                            url="https://www.band.us/band/57375315",
                            label="Check FWA Sync Time",
                            emoji="🕐"
                        )
                    ]
                ),
                Text(content=(
                    "Please review the **FWA Sync Time** and confirm your availability by selecting the "
                    "corresponding button below:"
                )),
                Separator(divider=True),
                Text(content="✅ - If you are available to start."),
                Text(content="📅 - If you may be available to start."),
                Text(content="❌ - If you are unavailable to start."),
                Separator(divider=True),
                Text(content=(
                    "*Please note that if your availability changes, you can update your response by "
                    "selecting the appropriate button.*"
                )),
                Separator(divider=True),
                Text(content="## Rep Availability"),
                Text(content="\n".join(response_lines)),
                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Yes",
                            emoji="✅",
                            custom_id=f"war_response:yes_{message_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Maybe",
                            emoji="📅",
                            custom_id=f"war_response:maybe_{message_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.DANGER,
                            label="No",
                            emoji="❌",
                            custom_id=f"war_response:no_{message_id}"
                        ),
                    ]
                ),
            ]
        )
    ]

    # Update the message
    await ctx.interaction.edit_initial_response(components=components)

    # Send confirmation to user
    emoji_map = {"yes": "✅", "maybe": "📅", "no": "❌"}
    await ctx.respond(
        f"{emoji_map[response_type]} Your response has been recorded!",
        ephemeral=True
    )


async def band_checker_loop(mongo: MongoClient):
    """Main loop that checks BAND API every 30 seconds"""
    debug_print("[BAND Monitor] Starting BAND API monitoring task...")

    while True:
        try:
            debug_print(f"\n[BAND Monitor] Checking at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Fetch posts from BAND API
            data = await fetch_band_posts()

            if data and "result_code" in data and data["result_code"] == 1:
                posts = data.get("result_data", {}).get("items", [])

                if posts:
                    # Get the most recent post (assuming first post is newest)
                    latest_post = posts[0]
                    latest_post_key = latest_post.get('post_key')
                    latest_content = latest_post.get('content', '')

                    debug_print(f"[BAND Monitor] Latest post key: {latest_post_key}")

                    if latest_post_key:
                        # Get the last processed post from MongoDB
                        last_processed_doc = await mongo.fwa_band_data.find_one({"_id": "last_processed_post"})
                        last_processed_key = last_processed_doc.get("post_key") if last_processed_doc else None

                        # Only process if this is a NEW most recent post
                        if latest_post_key != last_processed_key:
                            debug_print(f"[BAND Monitor] New latest post detected!")

                            # Check if this new post contains war sync text
                            if "PLEASE stop searching when the window closes after 1.5 hours" in latest_content:
                                debug_print("[BAND Monitor] New post contains War Sync reminder!")
                                await send_war_sync_to_discord(latest_post)
                            else:
                                debug_print("[BAND Monitor] New post doesn't contain War Sync text.")

                            # Update the last processed post in MongoDB
                            await mongo.fwa_band_data.update_one(
                                {"_id": "last_processed_post"},
                                {"$set": {
                                    "post_key": latest_post_key,
                                    "content": latest_content,
                                    "processed_at": datetime.now().isoformat()
                                }},
                                upsert=True
                            )
                            debug_print(f"[BAND Monitor] Updated last processed post to: {latest_post_key}")
                        else:
                            debug_print("[BAND Monitor] No new posts since last check.")
                    else:
                        debug_print("[BAND Monitor] Latest post has no post_key")
                else:
                    debug_print("[BAND Monitor] No posts found in API response")
            else:
                error_msg = data.get('result_msg', 'Unknown error') if data else 'Failed to fetch data'
                debug_print(f"[BAND Monitor] API Error: {error_msg}")

        except Exception as e:
            debug_print(f"[BAND Monitor] Error in loop: {type(e).__name__}: {e}")

        # Wait 30 seconds before next check
        debug_print("\n[BAND Monitor] Waiting 30 seconds until next check...")
        await asyncio.sleep(300)


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Start the BAND monitor task when bot starts"""
    global band_check_task, bot_instance, mongo_client

    # Store bot instance for sending messages
    bot_instance = event.app
    mongo_client = mongo

    # Create the task with mongo passed in
    band_check_task = asyncio.create_task(band_checker_loop(mongo))
    debug_print("[BAND Monitor] Background task started!")


@loader.listener(hikari.StoppingEvent)
async def on_bot_stopping(event: hikari.StoppingEvent) -> None:
    """Cancel the task when bot is stopping"""
    global band_check_task

    if band_check_task and not band_check_task.done():
        band_check_task.cancel()
        try:
            await band_check_task
        except asyncio.CancelledError:
            pass
        debug_print("[BAND Monitor] Background task cancelled!")


@loader.command
class ToggleDebug(
    lightbulb.SlashCommand,
    name="toggle-debug",
    description="Toggle debug mode for BAND monitor",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        global DEBUG_MODE
        DEBUG_MODE = not DEBUG_MODE
        status = "ON" if DEBUG_MODE else "OFF"
        await ctx.respond(f"🔧 BAND Monitor debug mode: **{status}**", ephemeral=True)
        debug_print(f"[DEBUG] Debug mode toggled to: {status} by {ctx.user.username}")