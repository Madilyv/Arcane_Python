"""
Staff Dashboard Main Command
/staff dashboard - Interactive staff log management
"""

import lightbulb
import hikari

from extensions.commands.staff import staff
from utils.mongo import MongoClient
from .utils import is_leadership, get_all_staff_logs
from .embeds import build_main_dashboard, build_empty_state_dashboard


@staff.register()
class StaffDashboard(
    lightbulb.SlashCommand,
    name="dashboard",
    description="Manage staff logs and employment records"
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        mongo: MongoClient = lightbulb.di.INJECTED
    ) -> None:
        await ctx.defer(ephemeral=True)  # Thinking message is ephemeral

        # Permission check - leadership only
        if not is_leadership(ctx.member):
            await ctx.respond(
                "❌ **Access Denied**\n\nOnly leadership can access the staff dashboard.",
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        # Get all staff logs for stats
        all_logs = await get_all_staff_logs(mongo)

        # Check if empty state - show quick start wizard
        if not all_logs:
            components = build_empty_state_dashboard(ctx.guild_id)
            # Send to channel as public message
            await bot.rest.create_message(channel=ctx.channel_id, components=components)
            # Delete the thinking message
            await ctx.interaction.delete_initial_response()
            print(f"[Staff Dashboard] Opened by {ctx.user.username} - EMPTY STATE")
            return

        # Calculate stats
        stats = {
            'active': sum(1 for log in all_logs if log.get('employment_status') == 'Active'),
            'on_leave': sum(1 for log in all_logs if log.get('employment_status') == 'On Leave'),
            'inactive': sum(1 for log in all_logs if log.get('employment_status') in ['Inactive', 'Terminated', 'Staff Banned'])
        }

        # Build main dashboard with categorized sections
        components = build_main_dashboard(ctx.guild_id, stats, all_logs)

        # Send dashboard to channel as public message
        await bot.rest.create_message(channel=ctx.channel_id, components=components)

        # Delete the ephemeral thinking message
        await ctx.interaction.delete_initial_response()
        print(f"[Staff Dashboard] Opened by {ctx.user.username}")
