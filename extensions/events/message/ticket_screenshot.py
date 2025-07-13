"""
Ticket Screenshot Verification System
Waits for user to send a message, then reminds them to upload a screenshot if they didn't.
Does NOT upload or store images - just verifies that an image was sent.
"""

import asyncio
import aiohttp
from utils.mongo import MongoClient
import hikari
import lightbulb
from datetime import datetime, timedelta
from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)
from utils.constants import RED_ACCENT, GREEN_ACCENT
from extensions.components import register_action

# CONFIGURABLE TIMEOUT - Adjust this value as needed
REMINDER_COOLDOWN_SECONDS = 10  # Don't send reminder again within this time
SCREENSHOT_PROCESSING_DELAY = 1  # Wait this many seconds for image to fully upload
REMINDER_DELETION_TIMEOUT = 15  # Auto-delete reminder after this many seconds

# Create loader
loader = lightbulb.Loader()

# Global variables to store instances (following your pattern)
mongo_client = None
bot_instance = None

# Store active screenshot verification sessions
screenshot_sessions = {}

# Store last reminder times to prevent spam
last_reminder_times = {}

# Store users who have already uploaded screenshots
completed_screenshots = {}  # Format: {ticket_id_user_id: True}

# Active ticket patterns (same as ticket_close_monitor.py)
PATTERNS = {
    "TEST": "𝕋𝔼𝕊𝕋",
    # "CLAN": "ℂ𝕃𝔸ℕ",  # Disabled for now
    # "FWA": "𝔽𝕎𝔸",    # Disabled for now
}

# Define which patterns are currently active
ACTIVE_PATTERNS = ["TEST"]


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Store instances when bot starts"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = event.app
    print("[INFO] Ticket screenshot verification ready")

    # Check for pending screenshot tickets
    await check_pending_screenshot_tickets(bot_instance, mongo_client)


async def check_pending_screenshot_tickets(bot: hikari.GatewayBot, mongo_client):
    """Check for tickets awaiting screenshots after bot restart"""
    if not mongo_client:
        return

    try:
        # Check if collection exists by trying to find one document
        test = await mongo_client.ticket_automation_state.find_one({})
        if test is None:
            print("[Screenshot] ticket_automation_state collection is empty or doesn't exist")
            return

        # Find all active tickets in screenshot step
        cursor = mongo_client.ticket_automation_state.find({
            "automation_state.status": "active",
            "automation_state.current_step": "awaiting_screenshot",
            "step_data.screenshot.uploaded": False
        })

        # Convert cursor to list using async iteration
        pending_tickets = []
        async for ticket in cursor:
            pending_tickets.append(ticket)

        print(f"[Screenshot] Found {len(pending_tickets)} tickets awaiting screenshots after restart")

        for ticket in pending_tickets:
            channel_id = ticket["_id"]
            user_id = ticket["ticket_info"]["user_id"]

            # Restore to completed_screenshots if already uploaded
            if ticket.get("step_data", {}).get("screenshot", {}).get("uploaded", False):
                completed_key = f"{channel_id}_{user_id}"
                completed_screenshots[completed_key] = True

    except AttributeError as e:
        print(f"[Screenshot] Collection 'ticket_automation_state' might not exist. Create it in MongoDB first.")
        print(f"[Screenshot] Run: db.createCollection('ticket_automation_state') in MongoDB")
    except Exception as e:
        print(f"[Screenshot] Error checking pending tickets: {type(e).__name__}: {e}")


@loader.listener(hikari.MessageCreateEvent)
async def on_message_in_ticket(event: hikari.MessageCreateEvent) -> None:
    """
    Listen for messages in ticket channels.
    If user sends a message without screenshot, remind them.
    If user sends a screenshot, show success message.
    """

    # Ignore bot messages
    if event.is_bot or event.is_webhook:
        return

    # Get channel info
    try:
        channel = await event.app.rest.fetch_channel(event.channel_id)
    except:
        return

    # Check if channel name contains any active pattern
    is_ticket_channel = False
    for pattern_key in ACTIVE_PATTERNS:
        if pattern_key in PATTERNS and PATTERNS[pattern_key] in channel.name:
            is_ticket_channel = True
            break

    if not is_ticket_channel:
        return

    # Use channel ID as ticket ID
    ticket_id = str(event.channel_id)
    user_id = event.author_id
    session_key = f"{ticket_id}_{user_id}"

    # Check ticket state from MongoDB
    if mongo_client:
        try:
            ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": ticket_id})

            if not ticket_state:
                # No ticket state found, this might be an old ticket
                print(f"[Screenshot] No ticket state found for channel {ticket_id}")
                return

            # Check if we're in the screenshot step
            current_step = ticket_state.get("automation_state", {}).get("current_step")
            if current_step != "awaiting_screenshot":
                # Not in screenshot step, ignore messages
                print(f"[Screenshot] Ticket {ticket_id} is in step '{current_step}', not awaiting screenshot")
                return

            # Check if screenshot already uploaded
            screenshot_data = ticket_state.get("step_data", {}).get("screenshot", {})
            if screenshot_data.get("uploaded"):
                # Already uploaded, no need to process
                return

        except Exception as e:
            print(f"[Screenshot] Error checking ticket state: {type(e).__name__}: {e}")
            # Continue anyway in case it's a connection issue

    # Check if message has image attachments
    has_image = any(
        attachment.media_type and attachment.media_type.startswith("image/")
        for attachment in event.message.attachments
    ) if event.message.attachments else False

    if has_image:
        # User sent a screenshot! Wait a moment for upload to complete
        await asyncio.sleep(SCREENSHOT_PROCESSING_DELAY)  # Wait for image to fully upload
        await handle_screenshot_upload(event, ticket_id, user_id, session_key)
    else:
        # User sent message without screenshot - check if we should remind them
        await maybe_send_reminder(event, ticket_id, user_id, session_key)


async def maybe_send_reminder(event: hikari.MessageCreateEvent, ticket_id: str, user_id: int, session_key: str):
    """Send reminder if cooldown has passed and user hasn't uploaded screenshot yet"""

    # Check if user already uploaded screenshot for this ticket
    completed_key = f"{ticket_id}_{user_id}"
    if completed_key in completed_screenshots:
        # User already uploaded, don't send reminder
        return

    # Check cooldown
    last_reminder_key = f"{ticket_id}_{user_id}"
    last_reminder = last_reminder_times.get(last_reminder_key)

    if last_reminder:
        time_since_reminder = (datetime.now() - last_reminder).total_seconds()
        if time_since_reminder < REMINDER_COOLDOWN_SECONDS:
            # Still in cooldown, don't send reminder
            return

    # Send reminder
    reminder_session_key, reminder_msg_id = await send_screenshot_reminder(event.app, event.channel_id, user_id)

    # Update last reminder time
    last_reminder_times[last_reminder_key] = datetime.now()

    # Update MongoDB with reminder info
    if mongo_client and reminder_msg_id:
        try:
            await mongo_client.ticket_automation_state.update_one(
                {"_id": ticket_id},
                {
                    "$set": {
                        "step_data.screenshot.reminder_sent": True,
                        "step_data.screenshot.last_reminder_at": datetime.now(),
                        "messages.screenshot_reminder": str(reminder_msg_id),
                        "last_updated": datetime.now()
                    },
                    "$inc": {
                        "step_data.screenshot.reminder_count": 1
                    },
                    "$push": {
                        "interaction_history": {
                            "timestamp": datetime.now(),
                            "action": "screenshot_reminder_sent",
                            "details": f"Reminder sent to user {user_id}"
                        }
                    }
                }
            )
        except Exception as e:
            print(f"[Screenshot] Error updating reminder info: {type(e).__name__}: {e}")


async def send_screenshot_reminder(bot: hikari.GatewayBot, channel_id: int, user_id: int):
    """Send the 'waiting for screenshot' message"""

    # Create session key
    ticket_id = str(channel_id)
    session_key = f"{ticket_id}_{user_id}_{int(datetime.now().timestamp())}"

    # Create the RED "waiting" components with user ping
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"## <@{user_id}>"),
                Text(content="📸 **Screenshot Required**"),
                Text(content=(
                    "Please upload a screenshot of your base to continue with your application.\n\n"
                    "**Instructions:**\n"
                    "• Take a clear screenshot of your Home Village\n"
                    "• Upload it directly in this channel\n"
                    "• The bot will automatically detect and process it"
                )),
                Separator(divider=True),
                Text(content="Your base helps us match you to the best clan!"),
                Text(content=f"-# This reminder will auto-delete in {REMINDER_DELETION_TIMEOUT} seconds"),
                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
            ]
        )
    ]

    # Send the reminder message
    reminder_msg = await bot.rest.create_message(
        channel=channel_id,
        components=components,
        user_mentions=True  # Enable user ping
    )

    # Schedule auto-deletion
    async def delete_reminder():
        await asyncio.sleep(REMINDER_DELETION_TIMEOUT)
        try:
            await bot.rest.delete_message(channel_id, reminder_msg)
            print(f"[Screenshot] Auto-deleted reminder message {reminder_msg.id}")
        except Exception as e:
            print(f"[Screenshot] Failed to auto-delete reminder: {e}")

    # Start deletion task
    asyncio.create_task(delete_reminder())

    # Store session info
    screenshot_sessions[session_key] = {
        "ticket_id": ticket_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "reminder_message_id": reminder_msg.id,
        "timestamp": datetime.now(),
        "screenshot_received": False
    }

    # Also store in MongoDB for persistence
    if mongo_client:
        await mongo_client.button_store.insert_one({
            "_id": f"screenshot_session_{session_key}",
            "message_id": reminder_msg.id,
            "channel_id": channel_id,
            "user_id": user_id,
            "ticket_id": ticket_id,
            "session_key": session_key
        })

    return session_key, reminder_msg.id


async def handle_screenshot_upload(event: hikari.MessageCreateEvent, ticket_id: str, user_id: int, session_key: str):
    """Handle when user uploads a screenshot"""

    # Mark user as having uploaded screenshot
    completed_key = f"{ticket_id}_{user_id}"
    completed_screenshots[completed_key] = True

    # Clear cooldown for this user
    last_reminder_key = f"{ticket_id}_{user_id}"
    if last_reminder_key in last_reminder_times:
        del last_reminder_times[last_reminder_key]

    # Update MongoDB state
    if mongo_client:
        try:
            # Update that screenshot was uploaded
            await mongo_client.ticket_automation_state.update_one(
                {"_id": ticket_id},
                {
                    "$set": {
                        "step_data.screenshot.uploaded": True,
                        "step_data.screenshot.uploaded_at": datetime.now(),
                        "automation_state.current_step": "clan_selection",  # Move to next step
                        "last_updated": datetime.now()
                    },
                    "$push": {
                        "automation_state.completed_steps": {
                            "step_name": "screenshot_uploaded",
                            "completed_at": datetime.now(),
                            "data": {"user_id": str(user_id)}
                        },
                        "interaction_history": {
                            "timestamp": datetime.now(),
                            "action": "screenshot_uploaded",
                            "details": f"User {user_id} uploaded screenshot"
                        }
                    },
                    "$inc": {
                        "automation_state.current_step_index": 1
                    }
                }
            )
            print(f"[Screenshot] Updated ticket state to clan_selection")
        except Exception as e:
            print(f"[Screenshot] Error updating ticket state: {type(e).__name__}: {e}")

    # Create the GREEN "success" components
    success_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="✅ **Thanks for the Screenshot!**"),
                Text(content=(
                    "Thank you for sharing your base screenshot! 🎉\n\n"
                    "We're now ready to move forward with the next step of the process."
                )),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                Text(content="**Kings Alliance Recruitment - Let's keep things moving!**"),
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id=f"continue_after_screenshot:{ticket_id}:{user_id}",
                        label="Continue to Next Step"
                    )
                ]),
                Media(items=[MediaItem(media="assets/Green_Footer.png")]),
            ]
        )
    ]

    # Always send a new success message
    try:
        await event.app.rest.create_message(
            channel=event.channel_id,
            components=success_components
        )
        print(f"[Screenshot] User {user_id} sent screenshot in ticket {ticket_id} - sent success message")

        # Clean up any sessions from memory
        for key in list(screenshot_sessions.keys()):
            if screenshot_sessions[key]["user_id"] == user_id and screenshot_sessions[key]["ticket_id"] == ticket_id:
                del screenshot_sessions[key]

        # Clean up MongoDB button store entries
        if mongo_client:
            try:
                # Delete any screenshot session entries for this user/ticket
                await mongo_client.button_store.delete_many({
                    "_id": {"$regex": f"^screenshot_session_"},
                    "user_id": user_id,
                    "ticket_id": ticket_id
                })
            except Exception as e:
                print(f"[Screenshot] Error cleaning up button store: {e}")

    except Exception as e:
        print(f"[Screenshot] Failed to send success message: {e}")


# ╔══════════════════════════════════════════════════════════╗
# ║                Continue Button Handler                    ║
# ╚══════════════════════════════════════════════════════════╝

@register_action("continue_after_screenshot", no_return=True)
async def continue_after_screenshot(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle the continue button after screenshot verification"""
    # Parse action_id: "ticket_id:user_id"
    parts = action_id.split(":")
    ticket_id = parts[0]
    user_id = parts[1]

    # Use DEFERRED_MESSAGE_UPDATE to update the current message
    await ctx.interaction.create_initial_response(
        hikari.ResponseType.DEFERRED_MESSAGE_UPDATE
    )

    # Update message to show next step
    # TODO: Replace this with your actual next step
    next_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="🚀 **Moving Forward!**"),
                Text(content=(
                    "Great! We've verified your screenshot.\n\n"
                    "The next step in your recruitment process will appear here."
                )),
                # Add your next step components here
                Media(items=[MediaItem(media="assets/Green_Footer.png")]),
            ]
        )
    ]

    await ctx.interaction.edit_initial_response(components=next_components)