# extensions/commands/moderation/delete_old_threads.py
import lightbulb
import hikari
from datetime import datetime, timedelta, timezone

loader = lightbulb.Loader()

# Target channel ID
CLAN_THREADS_CHANNEL = 1133096989748363294


@loader.command
class DeleteOldThreads(
    lightbulb.SlashCommand,
    name="delete-old-threads",
    description="Delete threads in clan channel that haven't been updated in 7 days",
    default_member_permissions=hikari.Permissions.MANAGE_THREADS
):
    @lightbulb.invoke
    async def invoke(
            self,
            ctx: lightbulb.Context,
            bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)

        # Calculate the cutoff date (7 days ago)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        # Counters for feedback
        threads_deleted = 0
        threads_checked = 0
        errors = []
        threads_to_delete = []

        try:
            # Fetch active threads for the guild
            active_threads = await bot.rest.fetch_active_threads(ctx.guild_id)

            # Filter threads belonging to our target channel
            target_threads = [t for t in active_threads if t.parent_id == CLAN_THREADS_CHANNEL]

            # Check each active thread for last activity
            for thread in target_threads:
                threads_checked += 1
                try:
                    # Fetch the most recent message
                    messages = await bot.rest.fetch_messages(thread.id).limit(1)
                    messages_list = list(messages)

                    if messages_list:
                        last_message = messages_list[0]
                        if last_message.created_at < cutoff_date:
                            threads_to_delete.append(
                                (thread, f"Last message: {last_message.created_at.strftime('%Y-%m-%d')}"))
                    else:
                        # No messages, check thread creation
                        if thread.created_at < cutoff_date:
                            threads_to_delete.append(
                                (thread, f"Empty thread created: {thread.created_at.strftime('%Y-%m-%d')}"))

                except Exception as e:
                    errors.append(f"Error checking thread {thread.name}: {str(e)}")

            # Delete the threads we identified
            for thread, reason in threads_to_delete:
                try:
                    await bot.rest.delete_channel(thread.id)
                    threads_deleted += 1
                    print(f"[INFO] Deleted thread: {thread.name} ({reason})")
                except hikari.ForbiddenError:
                    errors.append(f"No permission to delete thread: {thread.name}")
                except Exception as e:
                    errors.append(f"Error deleting thread {thread.name}: {str(e)}")

            # Build response message
            response = f"🧹 **Thread Cleanup Complete**\n\n"
            response += f"• Threads checked: {threads_checked}\n"
            response += f"• Threads deleted: {threads_deleted}\n"
            response += f"• Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M UTC')}\n"

            if errors:
                response += f"\n⚠️ **Errors encountered:**\n"
                for error in errors[:5]:
                    response += f"• {error}\n"
                if len(errors) > 5:
                    response += f"• ... and {len(errors) - 5} more errors\n"

            # Send response within the 3-second window
            await ctx.respond(response)

        except Exception as e:
            await ctx.respond(
                f"❌ **Command failed:** {str(e)}\n"
                f"Please check bot permissions and try again."
            )