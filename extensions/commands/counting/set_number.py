# extensions/commands/counting/set_number.py
"""
Set the next expected number for the counting channel.
"""

import hikari
import lightbulb
from utils.mongo import MongoClient
from . import loader, counting

@counting.register()
class SetNumber(
    lightbulb.SlashCommand,
    name="set-number",
    description="Set the next expected number for the counting channel",
):
    number = lightbulb.integer(
        "number",
        "The next number to expect",
        min_value=0
    )
    
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        
        # Check if user has manage channels permission
        if not ctx.member.permissions & hikari.Permissions.MANAGE_CHANNELS:
            await ctx.respond(
                "❌ You need the `Manage Channels` permission to use this command!",
                ephemeral=True
            )
            return
        
        channel_id = "1024845669820796928"  # Hardcoded counting channel ID
        
        # Update or insert counting channel data
        await mongo.counting_channels.update_one(
            {"channel_id": channel_id},
            {
                "$set": {
                    "channel_id": channel_id,
                    "current_number": self.number - 1,  # Store the last counted number
                    "last_counter_id": None,
                    "enabled": True
                }
            },
            upsert=True
        )
        
        await ctx.respond(
            f"✅ Counting channel configured! The next expected number is **{self.number}**",
            ephemeral=True
        )