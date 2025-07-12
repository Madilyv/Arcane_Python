# extensions/tasks/expire_new_recruits.py
"""Daily task to expire new recruits after 12 days"""

import asyncio
import lightbulb
import hikari
from datetime import datetime, timedelta, timezone

from utils.mongo import MongoClient

loader = lightbulb.Loader()

# Global variables
expire_task = None

# Configuration
CHECK_INTERVAL = 3600  # Check every hour (3600 seconds)


async def expire_old_recruits_loop(mongo: MongoClient):
    """Loop that checks for expired recruits periodically"""
    print("[New Recruits] Starting expiration check task...")

    while True:
        try:
            current_time = datetime.now(timezone.utc)
            print(f"[New Recruits] Running expiration check at {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Find and expire old recruits
            result = await mongo.new_recruits.update_many(
                {
                    "expires_at": {"$lte": current_time},
                    "is_expired": False
                },
                {"$set": {"is_expired": True}}
            )

            if result.modified_count > 0:
                print(f"[New Recruits] Expired {result.modified_count} new recruits")

                # Optional: Clean up very old expired recruits (> 30 days)
                cleanup_date = current_time - timedelta(days=30)
                cleanup_result = await mongo.new_recruits.delete_many({
                    "is_expired": True,
                    "expires_at": {"$lt": cleanup_date}
                })

                if cleanup_result.deleted_count > 0:
                    print(f"[New Recruits] Cleaned up {cleanup_result.deleted_count} old expired recruits")
            else:
                print(f"[New Recruits] No recruits to expire")

        except Exception as e:
            print(f"[ERROR] Failed to expire recruits: {type(e).__name__}: {e}")

        # Wait before next check
        await asyncio.sleep(CHECK_INTERVAL)


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
        event: hikari.StartedEvent,
        mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Start the expiration task when bot starts"""
    global expire_task

    # Create the task
    expire_task = asyncio.create_task(expire_old_recruits_loop(mongo))
    print("[New Recruits] Expiration check background task started!")


@loader.listener(hikari.StoppingEvent)
async def on_bot_stopping(event: hikari.StoppingEvent) -> None:
    """Cancel the task when bot is stopping"""
    global expire_task

    if expire_task and not expire_task.done():
        expire_task.cancel()
        try:
            await expire_task
        except asyncio.CancelledError:
            pass
        print("[New Recruits] Expiration check task cancelled!")


# Manual command to force expire check
@loader.command
class ExpireRecruits(
    lightbulb.SlashCommand,
    name="expire-recruits",
    description="Manually run the new recruit expiration check",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
            self,
            ctx: lightbulb.Context,
            mongo: MongoClient = lightbulb.di.INJECTED
    ) -> None:
        """Manually trigger recruit expiration"""
        await ctx.respond("🔄 Running recruit expiration check...", ephemeral=True)

        try:
            current_time = datetime.now(timezone.utc)

            # Expire old recruits
            result = await mongo.new_recruits.update_many(
                {
                    "expires_at": {"$lte": current_time},
                    "is_expired": False
                },
                {"$set": {"is_expired": True}}
            )

            # Clean up very old ones
            cleanup_date = current_time - timedelta(days=30)
            cleanup_result = await mongo.new_recruits.delete_many({
                "is_expired": True,
                "expires_at": {"$lt": cleanup_date}
            })

            await ctx.edit_last_response(
                f"✅ Expiration check complete!\n"
                f"• Expired: {result.modified_count} recruits\n"
                f"• Cleaned up: {cleanup_result.deleted_count} old records"
            )

        except Exception as e:
            await ctx.edit_last_response(f"❌ Failed to run expiration check: {str(e)}")