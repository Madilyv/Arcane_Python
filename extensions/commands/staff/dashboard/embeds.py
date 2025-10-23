"""
Staff Dashboard Embed Builders
Builds forum embeds and dashboard views using Components v2
"""

import hikari
import time
from datetime import datetime, timezone
from hikari.impl import (
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ThumbnailComponentBuilder as Thumbnail,
    SelectMenuBuilder as SelectMenu,
    TextSelectMenuBuilder as TextSelectMenu,
    InteractiveButtonBuilder as Button,
    LinkButtonBuilder as LinkButton,
    MessageActionRowBuilder as ActionRow,
)

from utils.constants import BLUE_ACCENT, GREEN_ACCENT, GOLD_ACCENT, RED_ACCENT, DARK_GRAY_ACCENT, STAFF_CASE_TYPES, get_all_teams, get_positions_for_team
from .utils import format_discord_timestamp, get_status_emoji, get_forum_thread_url


def build_staff_select_menu(all_logs: list, unique_id: str = "") -> TextSelectMenu:
    """
    Builds a TextSelectMenu with current staff members
    """
    # Sort logs by username
    sorted_logs = sorted(all_logs, key=lambda x: x.get('username', 'Unknown').lower())

    # Build options (max 25 for Discord limit)
    options = []
    for log in sorted_logs[:25]:
        user_id = log.get('user_id')
        username = log.get('username', 'Unknown')
        team = log.get('current_team', 'N/A')
        position = log.get('current_position', 'N/A')
        status = log.get('employment_status', 'Active')

        # Add status emoji
        status_emoji = get_status_emoji(status)

        options.append(
            hikari.impl.SelectOptionBuilder(
                label=f"{status_emoji} {username}",
                value=user_id,
                description=f"{team} - {position}"
            )
        )

    # Create unique custom_id by appending unique_id if provided
    custom_id = f"staff_dash_select_user:{unique_id}" if unique_id else "staff_dash_select_user"

    return TextSelectMenu(
        custom_id=custom_id,
        placeholder="🔍 Select Staff Member...",
        options=options,
        min_values=1,
        max_values=1
    )


def build_forum_embed(user: hikari.User, log_data: dict) -> list:
    """
    Builds the forum post embed matching the exact format from example
    This is what gets posted/edited in the forum thread
    """
    username = log_data.get('username', str(user))
    join_date = log_data.get('join_date')
    hire_date = log_data.get('hire_date')
    status = log_data.get('employment_status', 'Active')
    team = log_data.get('current_team', 'N/A')
    position = log_data.get('current_position', 'N/A')
    position_history = log_data.get('position_history', [])
    admin_changes = log_data.get('admin_changes', [])
    staff_cases = log_data.get('staff_cases', [])
    last_updated = log_data.get('metadata', {}).get('last_updated')

    # Case type emoji mapping (matches dropdown emojis)
    case_emojis = {
        "Warning": "⚠️",
        "Suspension": "⏸️",
        "Termination": "🔴",
        "Staff Ban": "🚫",
        "Note": "📝"
    }

    # Build position history text with enhanced details (newest first)
    # Try building with ALL entries first (smart display)
    def build_position_text(entries):
        """Helper to build position text from list of entries"""
        lines = []
        for idx, entry in enumerate(entries):
            # Determine action type
            action = entry.get('action')
            if action == 'removed':
                action_label = "❌ Removed"
            elif action == 'added':
                action_label = "➕ Added"
            elif action == 'updated':
                action_label = "🔄 Updated"
            elif idx == len(entries) - 1:
                # Last item in reversed array = oldest entry = initial hire
                action_label = "🟢 Hired"
            else:
                action_label = "🔄 Updated"

            # Get entry details
            team_name = entry.get('team', 'Unknown')
            pos_name = entry.get('position', 'Unknown')
            changed_by = entry.get('changed_by_name', 'Unknown')
            notes = entry.get('notes', '')
            date_str = format_discord_timestamp(entry.get('date'), "F")

            # Build entry
            lines.append(f"{action_label}: {team_name} - {pos_name}")

            # For updates with old position data, show transfer info
            if action == 'updated' and entry.get('old_team') and entry.get('old_position'):
                old_team = entry.get('old_team', 'Unknown')
                old_position = entry.get('old_position', 'Unknown')
                lines.append(f"   └ Transferred from: {old_team} - {old_position}")

            lines.append(f"   └ By: {changed_by} • {date_str}")
            if notes:
                lines.append(f"   └ Notes: {notes}")
            lines.append("")  # Blank line between entries

        return "\n".join(lines)

    # Build with ALL position history entries
    reversed_history = list(reversed(position_history))
    position_text = build_position_text(reversed_history) if reversed_history else "No position history"

    # Smart limiting: Only truncate if exceeds Discord's limit
    total_position_entries = len(position_history)
    if len(position_text) > 3500 and total_position_entries > 15:
        # Rebuild with only last 15 entries
        position_text = build_position_text(reversed_history[:15])
        position_text += f"\n-# ⚠️ Showing 15 of {total_position_entries} position changes (character limit reached)"

    # Build admin changes text with smart limiting
    def build_admin_text(changes):
        """Helper to build admin changes text from list of changes"""
        lines = []
        for change in changes:
            action = change.get('action', 'Unknown')
            date_str = format_discord_timestamp(change.get('date'), "F")
            reason = change.get('reason', 'No reason provided')
            lines.append(f"Admin {action}: {date_str}")
            lines.append(f"Reason: {reason}")
            lines.append("")  # Blank line
        return "\n".join(lines)

    # Build with ALL admin changes (reversed for newest first)
    reversed_admin = list(reversed(admin_changes))
    admin_text = build_admin_text(reversed_admin) if reversed_admin else ""

    # Smart limiting: Only truncate if exceeds Discord's limit
    total_admin_entries = len(admin_changes)
    if len(admin_text) > 3500 and total_admin_entries > 10:
        # Rebuild with only last 10 entries
        admin_text = build_admin_text(reversed_admin[:10])
        admin_text += f"\n-# ⚠️ Showing 10 of {total_admin_entries} admin changes (character limit reached)"

    # Build staff cases text (show only last 5 to prevent forum post from getting too long)
    case_lines = []
    recent_cases = list(reversed(staff_cases))[:5]  # Get last 5 cases (most recent first)
    total_cases = len(staff_cases)

    for case in recent_cases:
        case_type = case.get('type', 'Unknown')
        case_id = case.get('case_id', 0)
        date_str = format_discord_timestamp(case.get('date'), "F")
        reason = case.get('reason', 'No reason provided')
        issued_by = case.get('issued_by_name', 'Unknown')

        # Get emoji for case type
        case_emoji = case_emojis.get(case_type, "📋")

        case_lines.append(f"{case_emoji} {case_type} – Case ID: {case_id}")
        case_lines.append(f"   └ Issued by: {issued_by} • {date_str}")
        case_lines.append(f"   └ Reason: {reason}")
        case_lines.append("")  # Blank line

    cases_text = "\n".join(case_lines) if case_lines else ""

    # Add note if there are more cases than displayed
    if total_cases > 5:
        cases_text += f"\n-# Showing 5 of {total_cases} cases - View full history in staff dashboard"

    # Build component list FIRST (before Container instantiation)
    component_list = [
        # Header
        Section(
            accessory=Thumbnail(media=user.avatar_url or user.default_avatar_url),
            components=[
                Text(content=f"## {username} Staff Log"),
                Text(content=f"**User:** <@{user.id}>"),
            ]
        ),
        Separator(divider=True),

        # Basic Info
        Text(content=f"**Join Date:** {format_discord_timestamp(join_date, 'F')}"),
        Text(content=f"**Hire Date:** {format_discord_timestamp(hire_date, 'F')}"),
        Text(content=f"**Employment Status:** {status}"),
        Separator(divider=False, spacing=hikari.SpacingType.SMALL),
        Text(content="**Current Positions:**"),
        Text(content=f"• {team} - {position} (Primary)"),
        *[Text(content=f"• {pos.get('team', 'N/A')} - {pos.get('position', 'N/A')}")
          for pos in log_data.get('additional_positions', [])],

        Separator(divider=True),

        # Position Changes
        Text(content="### 📋 Position Changes"),
        Text(content=position_text),
    ]

    # Conditionally add admin changes section if any
    if admin_changes:
        component_list.append(Separator(divider=True))
        component_list.append(Text(content="### 🔑 Admin Changes"))
        component_list.append(Text(content=admin_text))

    # Conditionally add staff cases section if any
    if staff_cases:
        component_list.append(Separator(divider=True))
        component_list.append(Text(content="### ⚠️ Staff Cases"))
        component_list.append(Text(content=cases_text))

    # Add footer
    component_list.append(Separator(divider=False, spacing=hikari.SpacingType.SMALL))
    component_list.append(Text(content=f"-# Last Update • {format_discord_timestamp(last_updated, 'F')}"))

    # Build final Container with complete component list
    components = [
        Container(
            accent_color=DARK_GRAY_ACCENT,
            components=component_list
        )
    ]

    return components


def build_empty_state_dashboard(guild_id: int) -> list:
    """
    Builds the quick start wizard for when no staff logs exist
    """
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## 👥 Staff Log Dashboard"),
                Separator(divider=True),

                Text(content="### 📋 Getting Started"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content="Welcome to the Staff Log Management System!"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content="**This system helps you track:**"),
                Text(content="✓ Employment history and hire dates"),
                Text(content="✓ Position changes and promotions"),
                Text(content="✓ Admin rights modifications"),
                Text(content="✓ Staff cases, warnings, and commendations"),

                Separator(divider=True),

                Text(content="### 🎯 Quick Start Guide"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content="**Step 1:** Click the button below to create your first staff record"),
                Text(content="**Step 2:** Select the staff member from your server"),
                Text(content="**Step 3:** Fill in their employment details"),
                Text(content="**Step 4:** A dedicated forum thread will be created automatically"),

                Separator(divider=True),

                Text(content="**Ready to get started?**"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Create button
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Create First Staff Record",
                        custom_id="staff_dash_create_new",
                        emoji="🚀"
                    )
                ]),

                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content="-# No staff records found • Start by creating your first entry"),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_main_dashboard(guild_id: int, stats: dict, all_logs: list) -> list:
    """
    Builds the main dashboard view with categorized sections
    """
    active = stats.get('active', 0)
    on_leave = stats.get('on_leave', 0)
    inactive = stats.get('inactive', 0)
    total = active + on_leave + inactive

    # Generate unique ID for select menu to prevent Discord from caching selection state
    unique_id = str(int(time.time() * 1000))

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## 👥 Staff Log Dashboard"),
                Separator(divider=True),

                # ===== SECTION 1: OVERVIEW STATS =====
                Text(content="### 📊 Overview Stats"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content=f"**Total Staff:** {total} records"),
                Text(content=f"• {active} Active | {on_leave} On Leave | {inactive} Inactive"),

                Separator(divider=True),

                # ===== SECTION 2: BROWSE STAFF =====
                Text(content="### 🔍 Browse Staff"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content="Select a staff member to view their complete record:"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # User selection dropdown
                ActionRow(components=[
                    build_staff_select_menu(all_logs, unique_id)
                ]),

                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content="**Or filter by:**"),

                # Filter buttons
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="By Team",
                        custom_id="staff_dash_filter_role",
                        emoji="👥"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="By Status",
                        custom_id="staff_dash_filter_status",
                        emoji="📊"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Recent Changes",
                        custom_id="staff_dash_filter_recent",
                        emoji="🕒"
                    )
                ]),

                Separator(divider=True),

                # ===== SECTION 3: QUICK ACTIONS =====
                Text(content="### ⚡ Quick Actions"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Action buttons
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Create New Staff Log",
                        custom_id="staff_dash_create_new",
                        emoji="➕"
                    )
                ]),

                Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                Text(content="-# Use filters to browse staff by category or select directly from the dropdown"),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_staff_record_view(log: dict, user: hikari.User, guild_id: int, from_team_flow: bool = False) -> list:
    """
    Builds the staff record view with action buttons
    from_team_flow: If True, back button returns to team selection instead of closing
    """
    user_id = log.get('user_id')
    username = log.get('username', str(user))
    join_date = log.get('join_date')
    hire_date = log.get('hire_date')
    status = log.get('employment_status', 'Active')
    team = log.get('current_team', 'N/A')
    position = log.get('current_position', 'N/A')
    position_history = log.get('position_history', [])
    admin_changes = log.get('admin_changes', [])
    staff_cases = log.get('staff_cases', [])
    thread_id = log.get('forum_thread_id')

    # Determine accent color based on status
    accent_color = {
        "Active": GREEN_ACCENT,
        "On Leave": GOLD_ACCENT,
        "Inactive": "#808080",
        "Terminated": RED_ACCENT
    }.get(status, BLUE_ACCENT)

    # Get forum thread URL
    forum_url = get_forum_thread_url(guild_id, thread_id)

    components = [
        Container(
            accent_color=accent_color,
            components=[
                Section(
                    accessory=Thumbnail(media=user.avatar_url or user.default_avatar_url),
                    components=[Text(content=f"## 👤 {username} - Staff Log")]
                ),
                Separator(divider=True),

                # Basic info (consolidated)
                Text(content=f"**📅 Join Date:** {format_discord_timestamp(join_date, 'F')}\n**📅 Hire Date:** {format_discord_timestamp(hire_date, 'F')}\n**📊 Status:** {get_status_emoji(status)} {status}"),

                Separator(divider=True),

                # Current positions (primary + additional)
                Text(content="**Current Positions:**"),
                Text(content=f"• {team} - {position} (Primary)"),
                *[Text(content=f"• {pos.get('team', 'N/A')} - {pos.get('position', 'N/A')}")
                  for pos in log.get('additional_positions', [])],

                Separator(divider=True),

                # Summary stats (consolidated)
                Text(content=f"**📜 Position History:** {len(position_history)} | **🔑 Admin Changes:** {len(admin_changes)} | **⚠️ Cases:** {len(staff_cases)}"),

                Separator(divider=True),

                # Position Management Section
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Add Position",
                        custom_id=f"staff_dash_add_position:{user_id}",
                        emoji="➕"
                    ),
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        label="Update Position",
                        custom_id=f"staff_dash_position:{user_id}",
                        emoji="🔄"
                    ),
                    Button(
                        style=hikari.ButtonStyle.DANGER,
                        label="Remove Position",
                        custom_id=f"staff_dash_remove_position:{user_id}",
                        emoji="➖"
                    )
                ]),
                ActionRow(components=[
                    LinkButton(
                        url=forum_url,
                        label="View Full Log",
                        emoji="🔗"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Change Status",
                        custom_id=f"staff_dash_status:{user_id}",
                        emoji="📊"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Edit Info",
                        custom_id=f"staff_dash_edit:{user_id}",
                        emoji="📝"
                    )
                ]),

                Separator(divider=True),

                # Admin Controls Section
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        label="Admin Change",
                        custom_id=f"staff_dash_admin:{user_id}",
                        emoji="🔑"
                    ),
                    Button(
                        style=hikari.ButtonStyle.DANGER,
                        label="Add Case",
                        custom_id=f"staff_dash_case:{user_id}",
                        emoji="⚠️"
                    ),
                    Button(
                        style=hikari.ButtonStyle.DANGER,
                        label="Remove Case",
                        custom_id=f"staff_dash_remove_case:{user_id}",
                        emoji="🗑️"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="View Cases",
                        custom_id=f"staff_dash_view_cases:{user_id}",
                        emoji="📋"
                    )
                ]),

                Separator(divider=True),

                # Dangerous Operations Section
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.DANGER,
                        label="Delete Staff Log",
                        custom_id=f"staff_dash_delete_log:{user_id}",
                        emoji="🗑️"
                    )
                ]),

                Separator(divider=True),

                # Close/Back button
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back to Team Selection" if from_team_flow else "Close",
                        custom_id="staff_dash_return_team_selection" if from_team_flow else "staff_dash_back",
                        emoji="◀️" if from_team_flow else "✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_user_selection_for_creation(guild_id: int) -> list:
    """
    Builds the user selection view for creating a new staff log
    """
    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ➕ Create New Staff Log"),
                Separator(divider=True),

                Text(content="**Select the staff member** you want to create a log for:"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # User selection dropdown
                ActionRow(components=[
                    SelectMenu(
                        type=hikari.ComponentType.USER_SELECT_MENU,
                        custom_id="staff_dash_select_for_creation",
                        placeholder="🔍 Select Staff Member...",
                        min_values=1,
                        max_values=1
                    )
                ]),

                Separator(divider=True),

                Text(content="**Note:** After selecting a user, you'll be asked to enter:"),
                Text(content="• Hire date"),
                Text(content="• Server join date"),
                Text(content="• Staff team"),
                Text(content="• Position"),
                Text(content="• Employment status"),

                Separator(divider=True),

                # Back button
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Close",
                        custom_id="staff_dash_back",
                        emoji="✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_team_position_selection(guild_id: int, user: hikari.User, selected_team: str = None, selected_position: str = None) -> list:
    """
    Builds the team and position selection view for creating a staff log
    """
    # Get all teams
    teams = get_all_teams()

    # Use first team as default if none selected
    if selected_team is None:
        selected_team = teams[0]

    # Get positions for selected team
    positions = get_positions_for_team(selected_team)

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"## ➕ Create Staff Log for {user.mention}"),
                Separator(divider=True),

                Text(content="**Step 1:** Select the team"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Team selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_team_select:{user.id}",
                        placeholder="Select Team...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=team,
                                value=team,
                                is_default=(team == selected_team)
                            ) for team in teams
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 2:** Select the position"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Position selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_position_select:{user.id}:{selected_team}",
                        placeholder="Select Position...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=position,
                                value=position,
                                is_default=(position == selected_position) if selected_position else False
                            ) for position in positions
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 3:** Continue to set hire date"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Continue button - encode team:position in custom_id when both are selected
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Continue",
                        custom_id=(
                            f"staff_dash_continue_creation:{user.id}:{selected_team}:{selected_position}"
                            if selected_position
                            else f"staff_dash_continue_creation:{user.id}"
                        ),
                        emoji="✅"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Close",
                        custom_id="staff_dash_back",
                        emoji="✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_update_position_selection(guild_id: int, user_id: str, log: dict, position_identifier: str = "primary", selected_team: str = None, selected_position: str = None) -> list:
    """
    Builds the team and position selection view for updating an existing staff position
    Similar to build_team_position_selection but shows current position and is for updates
    """
    # Get current values based on position_identifier
    username = log.get('username', 'Unknown')
    additional_positions = log.get('additional_positions', [])

    if position_identifier == "primary":
        current_team = log.get('current_team', 'Unknown')
        current_position = log.get('current_position', 'Unknown')
        position_label = "⭐ Primary"
    else:
        # Parse "secondary_0", "secondary_1", etc.
        idx = int(position_identifier.split('_')[1])
        if idx < len(additional_positions):
            current_team = additional_positions[idx].get('team', 'Unknown')
            current_position = additional_positions[idx].get('position', 'Unknown')
            position_label = f"📋 Secondary #{idx + 1}"
        else:
            current_team = 'Unknown'
            current_position = 'Unknown'
            position_label = "Unknown Position"

    # Get all teams
    teams = get_all_teams()

    # Use current team as default if none selected
    if selected_team is None:
        selected_team = current_team if current_team in teams else teams[0]

    # Get positions for selected team
    positions = get_positions_for_team(selected_team)

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=f"## 🔄 Update Position for {username}"),
                Separator(divider=True),

                Text(content=f"**Updating:** {position_label}"),
                Text(content=f"**Current:** {current_team} - {current_position}"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content="**Step 1:** Select new team"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Team selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_update_team_select:{user_id}:{position_identifier}",
                        placeholder="Select Team...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=team,
                                value=team,
                                is_default=(team == selected_team)
                            ) for team in teams
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 2:** Select new position"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Position selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_update_position_select:{user_id}:{position_identifier}:{selected_team}",
                        placeholder="Select Position...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=position,
                                value=position,
                                is_default=(position == selected_position) if selected_position else False
                            ) for position in positions
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 3:** Confirm the update"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Update button - encode position_identifier:team:position in custom_id when both are selected
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Update Position",
                        custom_id=(
                            f"staff_dash_update_position_confirm:{user_id}:{position_identifier}:{selected_team}:{selected_position}"
                            if selected_position
                            else f"staff_dash_update_position_confirm:{user_id}"
                        ),
                        emoji="✅",
                        is_disabled=(not selected_position)
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back",
                        custom_id=f"staff_dash_view_record:{user_id}",
                        emoji="◀"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_add_position_selection(guild_id: int, user_id: str, log: dict, selected_team: str = None, selected_position: str = None) -> list:
    """
    Builds the team and position selection view for adding an additional position
    Staff member keeps existing positions and adds a new one
    """
    # Get current values for display
    current_team = log.get('current_team', 'Unknown')
    current_position = log.get('current_position', 'Unknown')
    additional_positions = log.get('additional_positions', [])
    username = log.get('username', 'Unknown')

    # Build current positions text
    positions_text = f"• {current_team} - {current_position} (Primary)"
    for pos in additional_positions:
        positions_text += f"\n• {pos.get('team', 'N/A')} - {pos.get('position', 'N/A')}"

    # Get all teams
    teams = get_all_teams()

    # Use first team as default if none selected
    if selected_team is None:
        selected_team = teams[0]

    # Get positions for selected team
    positions = get_positions_for_team(selected_team)

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"## ➕ Add Position for {username}"),
                Separator(divider=True),

                Text(content="**Current Positions:**"),
                Text(content=positions_text),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content="**Step 1:** Select team for new position"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Team selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_add_team_select:{user_id}",
                        placeholder="Select Team...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=team,
                                value=team,
                                is_default=(team == selected_team)
                            ) for team in teams
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 2:** Select position to add"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Position selection dropdown
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_add_position_select:{user_id}:{selected_team}",
                        placeholder="Select Position...",
                        options=[
                            hikari.impl.SelectOptionBuilder(
                                label=position,
                                value=position,
                                is_default=(position == selected_position) if selected_position else False
                            ) for position in positions
                        ]
                    )
                ]),

                Separator(divider=True),

                Text(content="**Step 3:** Confirm adding this position"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                # Add button - encode team:position in custom_id when both are selected
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Add Position",
                        custom_id=(
                            f"staff_dash_add_position_confirm:{user_id}:{selected_team}:{selected_position}"
                            if selected_position
                            else f"staff_dash_add_position_confirm:{user_id}"
                        ),
                        emoji="✅",
                        is_disabled=(not selected_position)
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back",
                        custom_id=f"staff_dash_view_record:{user_id}",
                        emoji="◀"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_remove_position_selection(guild_id: int, user_id: str, log: dict) -> list:
    """
    Builds the position selection view for removing a position
    Shows all positions (primary + secondary) with validation
    """
    current_team = log.get('current_team', 'Unknown')
    current_position = log.get('current_position', 'Unknown')
    additional_positions = log.get('additional_positions', [])
    username = log.get('username', 'Unknown')

    # Count total positions
    total_positions = 1 + len(additional_positions)

    # Build position options for dropdown
    position_options = []

    # Add primary position
    position_options.append(
        hikari.impl.SelectOptionBuilder(
            label=f"{current_team} - {current_position}",
            value="primary",
            description="Primary Position",
            emoji="⭐"
        )
    )

    # Add secondary positions
    for idx, pos in enumerate(additional_positions):
        position_options.append(
            hikari.impl.SelectOptionBuilder(
                label=f"{pos.get('team', 'N/A')} - {pos.get('position', 'N/A')}",
                value=f"secondary:{idx}",
                description="Secondary Position",
                emoji="📋"
            )
        )

    # Check if removal is allowed
    can_remove = total_positions > 1

    if not can_remove:
        # Show message that removal isn't possible
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=f"## ➖ Remove Position for {username}"),
                    Separator(divider=True),

                    Text(content="❌ **Cannot Remove Position**"),
                    Text(content=f"Staff member only has 1 position: **{current_team} - {current_position}**"),
                    Separator(divider=False, spacing=hikari.SpacingType.SMALL),
                    Text(content="-# Staff must have at least one position. Use 'Update Position' to change their role instead."),

                    Separator(divider=True),

                    ActionRow(components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Back",
                            custom_id=f"staff_dash_view_record:{user_id}",
                            emoji="◀"
                        )
                    ]),

                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]
    else:
        # Show position selection
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=f"## ➖ Remove Position for {username}"),
                    Separator(divider=True),

                    Text(content="**Select position to remove:**"),
                    Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                    ActionRow(components=[
                        TextSelectMenu(
                            custom_id=f"staff_dash_select_position_remove:{user_id}",
                            placeholder="Choose position to remove...",
                            options=position_options
                        )
                    ]),

                    Separator(divider=True),

                    Text(content="-# ⚠️ Removing a position will require a reason and will be logged in their history."),

                    ActionRow(components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Back",
                            custom_id=f"staff_dash_view_record:{user_id}",
                            emoji="◀"
                        )
                    ]),

                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

    return components


def build_which_position_to_update_selection(guild_id: int, user_id: str, log: dict) -> list:
    """
    Builds the position selection view for choosing which position to update
    Shows all positions (primary + secondary) when staff has multiple positions
    """
    current_team = log.get('current_team', 'Unknown')
    current_position = log.get('current_position', 'Unknown')
    additional_positions = log.get('additional_positions', [])
    username = log.get('username', 'Unknown')

    # Build position options for dropdown
    position_options = []

    # Add primary position
    position_options.append(
        hikari.impl.SelectOptionBuilder(
            label=f"{current_team} - {current_position}",
            value="primary",
            description="Primary Position",
            emoji="⭐"
        )
    )

    # Add secondary positions
    for idx, pos in enumerate(additional_positions):
        position_options.append(
            hikari.impl.SelectOptionBuilder(
                label=f"{pos.get('team', 'N/A')} - {pos.get('position', 'N/A')}",
                value=f"secondary_{idx}",
                description="Secondary Position",
                emoji="📋"
            )
        )

    # Show position selection
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=f"## 🔄 Update Position for {username}"),
                Separator(divider=True),

                Text(content="**Which position do you want to update?**"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_which_position_select:{user_id}",
                        placeholder="Choose position to update...",
                        options=position_options
                    )
                ]),

                Separator(divider=True),

                Text(content="-# Select the position you want to change, then choose the new team and role."),

                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back",
                        custom_id=f"staff_dash_view_record:{user_id}",
                        emoji="◀"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_remove_case_selection(guild_id: int, user_id: str, log: dict) -> list:
    """
    Builds the case selection view for removing a case
    Shows all cases for this staff member
    """
    username = log.get('username', 'Unknown')
    staff_cases = log.get('staff_cases', [])

    # Build case options for dropdown
    case_options = []

    if not staff_cases:
        # No cases to remove
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=f"## 🗑️ Remove Case for {username}"),
                    Separator(divider=True),

                    Text(content="❌ **No Cases Found**"),
                    Text(content=f"Staff member has no cases to remove."),

                    Separator(divider=True),

                    ActionRow(components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Back",
                            custom_id=f"staff_dash_view_record:{user_id}",
                            emoji="◀"
                        )
                    ]),

                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]
    else:
        # Show case selection
        for case in staff_cases:
            case_id = case.get('case_id', 'Unknown')
            case_type = case.get('type', 'Unknown')
            date = case.get('date')
            date_str = format_discord_timestamp(date, "d") if date else "Unknown Date"

            case_options.append(
                hikari.impl.SelectOptionBuilder(
                    label=f"[{case_id}] {case_type}",
                    value=case_id,
                    description=f"Issued: {date_str}",
                    emoji="⚠️"
                )
            )

        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=f"## 🗑️ Remove Case for {username}"),
                    Separator(divider=True),

                    Text(content="**Select case to remove:**"),
                    Text(content=f"Total cases: **{len(staff_cases)}**"),
                    Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                    ActionRow(components=[
                        TextSelectMenu(
                            custom_id=f"staff_dash_select_case_remove:{user_id}",
                            placeholder="Choose case to remove...",
                            options=case_options
                        )
                    ]),

                    Separator(divider=True),

                    Text(content="-# ⚠️ Removing a case will permanently delete it from the staff member's record."),

                    ActionRow(components=[
                        Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="Back",
                            custom_id=f"staff_dash_view_record:{user_id}",
                            emoji="◀"
                        )
                    ]),

                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

    return components


def build_case_type_selection(guild_id: int, user_id: str, username: str) -> list:
    """
    Builds the case type selection view for adding a case
    Shows dropdown with case type options
    """
    # Build case type options for dropdown
    case_type_options = []

    case_emojis = {
        "Warning": "⚠️",
        "Suspension": "⏸️",
        "Termination": "🔴",
        "Staff Ban": "🚫",
        "Note": "📝"
    }

    for case_type in STAFF_CASE_TYPES:
        emoji = case_emojis.get(case_type, "📋")
        case_type_options.append(
            hikari.impl.SelectOptionBuilder(
                label=case_type,
                value=case_type,
                emoji=emoji
            )
        )

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"## ⚠️ Add Case for {username}"),
                Separator(divider=True),

                Text(content="**Select case type:**"),
                Text(content="Choose the type of case to add to this staff member's record."),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"staff_dash_select_case_type:{user_id}",
                        placeholder="Choose case type...",
                        options=case_type_options
                    )
                ]),

                Separator(divider=True),

                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back",
                        custom_id=f"staff_dash_view_record:{user_id}",
                        emoji="◀"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_view_cases_menu(guild_id: int, user_id: str = None) -> list:
    """
    Builds the View Cases menu - choose between viewing all cases or searching by ID
    """
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## 📋 View Cases"),
                Separator(divider=True),

                Text(content="**Choose how to view cases:**"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        label="View All Cases",
                        custom_id=f"staff_dash_view_all_cases",
                        emoji="📋"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Search by Case ID",
                        custom_id=f"staff_dash_search_case_id",
                        emoji="🔍"
                    )
                ]),

                Separator(divider=True),

                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Back" if user_id else "Close",
                        custom_id=f"staff_dash_view_record:{user_id}" if user_id else "staff_dash_back",
                        emoji="◀" if user_id else "✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_all_cases_view(guild_id: int, all_logs: list) -> list:
    """
    Builds a view showing all cases across all staff members
    """
    # Collect all cases from all staff
    all_cases = []
    for log in all_logs:
        user_id = log.get('user_id')
        username = log.get('username', 'Unknown')
        staff_cases = log.get('staff_cases', [])

        for case in staff_cases:
            all_cases.append({
                'user_id': user_id,
                'username': username,
                'case_id': case.get('case_id'),
                'type': case.get('type'),
                'date': case.get('date'),
                'reason': case.get('reason'),
                'issued_by_name': case.get('issued_by_name')
            })

    # Sort by date (most recent first)
    all_cases.sort(key=lambda x: x.get('date', datetime.min), reverse=True)

    # Build case display
    case_lines = []
    for case in all_cases[:50]:  # Limit to 50 most recent
        case_id = case.get('case_id', 'Unknown')
        case_type = case.get('type', 'Unknown')
        username = case.get('username', 'Unknown')
        date_str = format_discord_timestamp(case.get('date'), "F")
        issued_by = case.get('issued_by_name', 'Unknown')

        case_lines.append(f"**[{case_id}]** {case_type} - {username}")
        case_lines.append(f"   └ Issued by: {issued_by} • {date_str}")
        case_lines.append("")

    cases_text = "\n".join(case_lines) if case_lines else "No cases found"

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## 📋 All Staff Cases"),
                Separator(divider=True),

                Text(content=f"**Total Cases:** {len(all_cases)}"),
                Text(content="-# Showing most recent 50 cases"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content=cases_text),

                Separator(divider=True),

                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Close",
                        custom_id="staff_dash_back",
                        emoji="✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components


def build_filter_view(guild_id: int, filter_type: str, filtered_logs: list, all_logs: list, unique_id: str = "") -> list:
    """
    Builds a filtered view showing staff that match the filter criteria
    """
    filter_emojis = {
        "team": "👥",
        "status": "📊",
        "role": "🎯",
        "recent": "🕒"
    }

    filter_titles = {
        "team": "By Team",
        "status": "By Status",
        "role": "By Role",
        "recent": "Recent Changes"
    }

    emoji = filter_emojis.get(filter_type, "🔍")
    title = filter_titles.get(filter_type, "Filtered View")

    total_count = len(all_logs)
    filtered_count = len(filtered_logs)

    # Build staff list text
    if filtered_logs:
        staff_lines = []
        for log in filtered_logs[:20]:  # Show max 20
            user_id = log.get('user_id')
            username = log.get('username', 'Unknown')
            status = log.get('employment_status', 'N/A')
            team = log.get('current_team', 'N/A')
            position = log.get('current_position', 'N/A')

            staff_lines.append(f"• <@{user_id}> - {status}")
            staff_lines.append(f"  {team}: {position}")

        staff_text = "\n".join(staff_lines)

        if len(filtered_logs) > 20:
            staff_text += f"\n\n-# ... and {len(filtered_logs) - 20} more"
    else:
        staff_text = "-# No staff found matching this filter"

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=f"## {emoji} Staff Filter: {title}"),
                Separator(divider=True),

                Text(content=f"**Showing {filtered_count} of {total_count} staff members**"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                Text(content=staff_text),

                Separator(divider=True),

                # User select for quick access
                Text(content="Select a staff member to view their record:"),
                Separator(divider=False, spacing=hikari.SpacingType.SMALL),

                ActionRow(components=[
                    build_staff_select_menu(filtered_logs, unique_id)
                ]),

                Separator(divider=True),

                # Back button
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Close",
                        custom_id="staff_dash_back",
                        emoji="✖️"
                    )
                ]),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    return components
