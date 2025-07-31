# extensions/commands/poll/active.py
"""
List active polls in the server.
"""

import hikari
import lightbulb
from datetime import datetime, timezone

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT
from . import loader, poll

@poll.register()
class Active(
    lightbulb.SlashCommand,
    name="active",
    description="List all active polls in this server",
):
    
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        
        # Find all active polls in this guild
        active_polls = await mongo.discord_polls.find({
            "guild_id": str(ctx.guild_id),
            "active": True
        }).sort("ends_at", 1).to_list(length=25)
        
        if not active_polls:
            await ctx.respond("📊 No active polls in this server", ephemeral=True)
            return
        
        # Create embed
        embed = hikari.Embed(
            title="📊 Active Polls",
            description=f"Found {len(active_polls)} active poll{'s' if len(active_polls) != 1 else ''}",
            color=BLUE_ACCENT,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add each poll
        for poll_data in active_polls[:10]:  # Show max 10
            # Calculate time remaining
            time_left = poll_data["ends_at"] - datetime.now(timezone.utc)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            
            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
            
            # Build field value
            field_value = [
                f"**Channel:** <#{poll_data['channel_id']}>",
                f"**Votes:** {len(poll_data['votes'])}",
                f"**Ends in:** {time_str}",
                f"**ID:** `{poll_data['_id']}`"
            ]
            
            if poll_data.get("message_id"):
                field_value.append(
                    f"[Jump to poll](https://discord.com/channels/{poll_data['guild_id']}/{poll_data['channel_id']}/{poll_data['message_id']})"
                )
            
            # Truncate description if too long
            description = poll_data["description"]
            if len(description) > 100:
                description = description[:97] + "..."
            
            embed.add_field(
                name=description,
                value="\n".join(field_value),
                inline=False
            )
        
        if len(active_polls) > 10:
            embed.set_footer(text=f"Showing 10 of {len(active_polls)} active polls")
        
        await ctx.respond(embed=embed, ephemeral=True)

loader.command(Active)