# commands/clan/report/__init__.py
"""Main entry point for clan points reporting system"""
import lightbulb
from extensions.commands.clan import loader, clan
from .router import create_home_dashboard

@clan.register()
class ReportPoints(
    lightbulb.SlashCommand,
    name="report-points",
    description="Report recruitment activities for clan points",
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context):
        """Initialize the reporting dashboard"""
        await ctx.respond(
            components=await create_home_dashboard(ctx.member),
            ephemeral=True
        )

# Import all report modules to register their actions
from . import discord_post
from . import dm_recruitment
from . import member_left
from . import approval
from . import router

# Register the clan group with the loader
loader.command(clan)