# extensions/tasks/disboard_reminder.py
"""
Scheduled task to send Disboard bump reminders every 12 hours.
Checks if 12+ hours have passed since last bump and sends reminder to bump channel.
"""

import asyncio
import hikari
import lightbulb
from datetime import datetime, timezone, timedelta
from typing import Optional

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    LinkButtonBuilder as LinkButton,
    MessageActionRowBuilder as ActionRow,
)

from utils.mongo import MongoClient
from utils.constants import (
    BLUE_ACCENT,
    BUMP_CHANNEL_ID,
    BUMP_ROLE_ID,
    DISBOARD_REVIEW_URL
)

loader = lightbulb.Loader()

# Configuration
CHECK_INTERVAL = 3600  # Check every hour (3600 seconds)
BUMP_COOLDOWN_HOURS = 12  # Remind after 12 hours

# Global variables
reminder_task = None
bot_instance = None
mongo_client = None


async def check_and_send_reminder():
    """Check if it's time to send a bump reminder"""
    if not mongo_client or not bot_instance:
        print("[Disboard Reminder] Clients not initialized")
        return

    try:
        # Get the last bump data from MongoDB
        bump_data = await mongo_client.disboard_bump.find_one({})

        if not bump_data:
            # No bump data exists, send initial reminder
            print("[Disboard Reminder] No bump data found, sending initial reminder")
            await send_bump_reminder(first_time=True)
            return

        # Get last bump timestamp
        last_bump_time = bump_data.get("last_bump_timestamp")
        last_reminder_time = bump_data.get("last_reminder_timestamp")

        if not last_bump_time:
            # No bump timestamp, send reminder
            print("[Disboard Reminder] No bump timestamp, sending reminder")
            await send_bump_reminder(first_time=True)
            return

        # Ensure timezone-aware datetime
        if last_bump_time.tzinfo is None:
            last_bump_time = last_bump_time.replace(tzinfo=timezone.utc)

        # Calculate time since last bump
        now = datetime.now(timezone.utc)
        time_since_bump = now - last_bump_time
        hours_since_bump = time_since_bump.total_seconds() / 3600

        print(f"[Disboard Reminder] Hours since last bump: {hours_since_bump:.2f}")

        # Check if 12+ hours have passed
        if hours_since_bump >= BUMP_COOLDOWN_HOURS:
            # Check if we've already sent a reminder recently (avoid spam)
            if last_reminder_time:
                if last_reminder_time.tzinfo is None:
                    last_reminder_time = last_reminder_time.replace(tzinfo=timezone.utc)

                time_since_reminder = now - last_reminder_time
                hours_since_reminder = time_since_reminder.total_seconds() / 3600

                # Only send reminder if it's been at least 1 hour since last reminder
                if hours_since_reminder < 1:
                    print(f"[Disboard Reminder] Already sent reminder recently ({hours_since_reminder:.2f} hours ago)")
                    return

            print("[Disboard Reminder] Sending bump reminder")
            await send_bump_reminder()

            # Update last reminder timestamp
            await mongo_client.disboard_bump.update_one(
                {},
                {"$set": {"last_reminder_timestamp": now}},
                upsert=True
            )
        else:
            remaining_hours = BUMP_COOLDOWN_HOURS - hours_since_bump
            print(f"[Disboard Reminder] Next reminder in {remaining_hours:.2f} hours")

    except Exception as e:
        print(f"[Disboard Reminder] Error checking reminder: {e}")


async def send_bump_reminder(first_time: bool = False):
    """Send a bump reminder message to the bump channel"""

    # Build the reminder message
    role_mention = f"<@&{BUMP_ROLE_ID}>"

    if first_time:
        title = "## 📢 It's Time to Bump!"
        intro_text = (
            f"{role_mention}\n\n"
            f"Help Kings Alliance reach more players by bumping our server!\n\n"
            f"Use the command </bump:947088344167366698> to bump now!"
        )
    else:
        title = "## ⏰ Bump Reminder!"
        intro_text = (
            f"{role_mention}\n\n"
            f"It's been 12 hours since our last bump! Help Kings Alliance grow by "
            f"bumping the server.\n\n"
            f"Use the command </bump:947088344167366698> to bump now!"
        )

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=title),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=intro_text),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "### 💎 **Earn Extra Clan Points!**\n"
                    "Don't forget: Your clan can gain **one extra point** for leaving a "
                    "**5-star review** with meaningful content on Disboard!"
                )),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "Share your experience with Kings Alliance and help us grow while "
                    "earning rewards for your clan!"
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                ActionRow(
                    components=[
                        LinkButton(
                            url=DISBOARD_REVIEW_URL,
                            label="Leave a 5⭐ Review",
                            emoji="⭐"
                        )
                    ]
                ),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    f"*After bumping, you'll need to wait 2 hours before the next bump.* ⏳"
                )),
                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    try:
        reminder_message = await bot_instance.rest.create_message(
            channel=BUMP_CHANNEL_ID,
            components=components,
            user_mentions=True,
            role_mentions=[BUMP_ROLE_ID]
        )
        print(f"[Disboard Reminder] Sent bump reminder message (ID: {reminder_message.id})")

        # Store the reminder message ID in MongoDB so we can delete it later
        await mongo_client.disboard_bump.update_one(
            {},
            {"$set": {"last_reminder_message_id": str(reminder_message.id)}},
            upsert=True
        )
        print(f"[Disboard Reminder] Stored reminder message ID: {reminder_message.id}")

    except Exception as e:
        print(f"[Disboard Reminder] Error sending reminder: {e}")


async def reminder_loop():
    """Main reminder loop that checks every hour"""
    print("[Disboard Reminder] Starting reminder monitoring task...")

    # Wait a bit for bot to fully initialize
    await asyncio.sleep(10)

    while True:
        try:
            print(f"[Disboard Reminder] Running check at {datetime.now(timezone.utc)}")
            await check_and_send_reminder()

            # Wait for next check
            await asyncio.sleep(CHECK_INTERVAL)

        except asyncio.CancelledError:
            print("[Disboard Reminder] Task cancelled")
            break
        except Exception as e:
            print(f"[Disboard Reminder] Error in reminder loop: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Start the reminder task when bot starts"""
    global reminder_task, bot_instance, mongo_client

    bot_instance = event.app
    mongo_client = mongo

    # Start the background task
    reminder_task = asyncio.create_task(reminder_loop())
    print("[Disboard Reminder] Background monitoring task started!")


@loader.listener(hikari.StoppingEvent)
async def on_bot_stopping(event: hikari.StoppingEvent) -> None:
    """Cancel the task when bot stops"""
    global reminder_task

    if reminder_task and not reminder_task.done():
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        print("[Disboard Reminder] Background task cancelled!")


# Manual command for testing/admin use
@loader.command
class TestBumpReminder(
    lightbulb.SlashCommand,
    name="test-bump-reminder",
    description="Manually trigger bump reminder (Admin only)",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("📢 Sending test bump reminder...", ephemeral=True)

        try:
            await send_bump_reminder()
            await ctx.edit_last_response("✅ Test reminder sent!")
        except Exception as e:
            await ctx.edit_last_response(f"❌ Failed to send reminder: {str(e)}")