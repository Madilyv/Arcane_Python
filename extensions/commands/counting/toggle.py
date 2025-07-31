# extensions/commands/counting/toggle.py
"""
Enable or disable the counting channel.
"""

import hikari
import lightbulb
from utils.mongo import MongoClient
from . import loader, counting

@counting.register()
class Toggle(
    lightbulb.SlashCommand,
    name="toggle",
    description="Enable or disable the counting channel",
):
    enabled = lightbulb.boolean(
        "enabled",
        "Enable or disable counting",
        default=True
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
        
        # Update counting channel status
        await mongo.counting_channels.update_one(
            {"channel_id": channel_id},
            {"$set": {"enabled": self.enabled}},
            upsert=True
        )
        
        status = "enabled" if self.enabled else "disabled"
        await ctx.respond(
            f"✅ Counting channel has been **{status}**!",
            ephemeral=True
        )