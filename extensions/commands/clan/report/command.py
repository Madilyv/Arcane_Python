# extensions/commands/clan/report/command.py
"""Main command entry point for clan points reporting"""

import lightbulb
import hikari
from extensions.commands.clan import loader, clan
from .utils import create_home_dashboard

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

# Register the clan group with the loader
loader.command(clan)