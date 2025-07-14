# extensions/events/message/ticket_automation/components/__init__.py
"""Component builders and templates for ticket automation"""

from .builders import (
    create_container_component,
    create_question_component,
    create_attack_strategy_components,
    create_clan_expectations_components,
    create_button
)

from .templates import (
    INTERVIEW_SELECTION_TEMPLATE,
    COMPLETION_TEMPLATE,
    ERROR_TEMPLATE
)

__all__ = [
    'create_container_component',
    'create_question_component',
    'create_attack_strategy_components',
    'create_clan_expectations_components',
    'create_button',
    'INTERVIEW_SELECTION_TEMPLATE',
    'COMPLETION_TEMPLATE',
    'ERROR_TEMPLATE'
]