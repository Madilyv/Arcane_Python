"""
Staff Dashboard Modals
Modal builders for data entry
"""

import hikari


def build_create_log_modal(selected_user_id: str, team: str, position: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for creating new staff log
    User and team/position are already selected, just need hire date
    Team and position are encoded in custom_id for retrieval
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="Create New Staff Log",
            custom_id=f"staff_dash_create_submit:{selected_user_id}:{team}:{position}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="hire_date",
                    label="Hire Date (YYYY-MM-DD)",
                    style=hikari.TextInputStyle.SHORT,
                    placeholder="2024-01-15",
                    required=True,
                )
            )
        )
    )


def build_position_modal(user_id: str, current_team: str, current_position: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for updating staff position
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="Update Staff Position",
            custom_id=f"staff_dash_position_submit:{user_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="team",
                    label="New Team",
                    style=hikari.TextInputStyle.SHORT,
                    value=current_team,
                    required=True,
                )
            )
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="position",
                    label="New Position",
                    style=hikari.TextInputStyle.SHORT,
                    value=current_position,
                    required=True,
                )
            )
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="notes",
                    label="Reason/Notes (optional)",
                    style=hikari.TextInputStyle.PARAGRAPH,
                    required=False,
                )
            )
        )
    )


def build_admin_modal(user_id: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for tracking admin changes
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="Admin Rights Change",
            custom_id=f"staff_dash_admin_submit:{user_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="action",
                    label="Action (Add or Remove)",
                    style=hikari.TextInputStyle.SHORT,
                    placeholder="Add",
                    required=True,
                )
            )
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="reason",
                    label="Reason",
                    style=hikari.TextInputStyle.PARAGRAPH,
                    placeholder="Reason for admin change...",
                    required=True,
                )
            )
        )
    )


def build_case_modal(user_id: str, case_type: str, action_id: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for adding staff case (reason only, case type selected previously)
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title=f"Add {case_type}",
            custom_id=f"staff_dash_case_submit:{action_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="reason",
                    label="Reason",
                    style=hikari.TextInputStyle.PARAGRAPH,
                    placeholder=f"Detailed reason for this {case_type.lower()}...",
                    required=True,
                )
            )
        )
    )


def build_status_modal(user_id: str, current_status: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for changing employment status
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="Change Employment Status",
            custom_id=f"staff_dash_status_submit:{user_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="status",
                    label="New Status",
                    style=hikari.TextInputStyle.SHORT,
                    placeholder="Active, On Leave, Inactive, Terminated",
                    value=current_status,
                    required=True,
                )
            )
        )
    )


def build_edit_modal(user_id: str, hire_date_str: str, join_date_str: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for editing basic info
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="Edit Staff Info",
            custom_id=f"staff_dash_edit_submit:{user_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="hire_date",
                    label="Hire Date (YYYY-MM-DD)",
                    style=hikari.TextInputStyle.SHORT,
                    value=hire_date_str,
                    required=True,
                )
            )
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="join_date",
                    label="Server Join Date (YYYY-MM-DD)",
                    style=hikari.TextInputStyle.SHORT,
                    value=join_date_str,
                    required=True,
                )
            )
        )
    )


def build_delete_confirmation_modal(user_id: str) -> hikari.impl.InteractionModalBuilder:
    """
    Modal for confirming staff log deletion
    Requires user to type DELETE to confirm
    """
    return (
        hikari.impl.InteractionModalBuilder(
            title="⚠️ Delete Staff Log - Confirmation",
            custom_id=f"staff_dash_delete_confirm:{user_id}",
        )
        .add_component(
            hikari.impl.MessageActionRowBuilder()
            .add_component(
                hikari.impl.TextInputBuilder(
                    custom_id="confirmation",
                    label="Type DELETE to confirm",
                    style=hikari.TextInputStyle.SHORT,
                    placeholder="DELETE",
                    required=True,
                    max_length=10
                )
            )
        )
    )
