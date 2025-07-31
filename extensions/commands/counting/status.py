# extensions/commands/counting/status.py
"""
Check the current counting channel status.
"""

import hikari
import lightbulb
from utils.mongo import MongoClient
from . import loader, counting

@counting.register()
class Status(
    lightbulb.SlashCommand,
    name="status",
    description="Check the current counting channel status",
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        
        channel_id = "1024845669820796928"  # Hardcoded counting channel ID
        
        # Get counting channel data
        data = await mongo.counting_channels.find_one({"channel_id": channel_id})
        
        if not data:
            await ctx.respond(
                "❌ Counting channel not configured yet! Use `/counting set-number` to set it up.",
                ephemeral=True
            )
            return
        
        current_number = data.get("current_number", 0)
        next_number = current_number + 1
        enabled = data.get("enabled", True)
        status_text = "enabled" if enabled else "disabled"
        
        # Get last counter info if available
        last_counter_info = ""
        if data.get("last_counter_id"):
            last_counter_info = f"\nLast counter: <@{data['last_counter_id']}>"
        
        await ctx.respond(
            f"📊 **Counting Channel Status**\n"
            f"Status: **{status_text}**\n"
            f"Current number: **{current_number}**\n"
            f"Next expected: **{next_number}**"
            f"{last_counter_info}",
            ephemeral=True
        )