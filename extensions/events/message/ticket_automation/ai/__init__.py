# extensions/events/message/ticket_automation/ai/__init__.py
"""AI processing functionality for ticket automation"""

from .processors import (
    process_attack_strategies_with_ai,
    process_clan_expectations_with_ai
)

from .prompts import (
    ATTACK_STRATEGIES_PROMPT,
    CLAN_EXPECTATIONS_PROMPT
)

__all__ = [
    'process_attack_strategies_with_ai',
    'process_clan_expectations_with_ai',
    'ATTACK_STRATEGIES_PROMPT',
    'CLAN_EXPECTATIONS_PROMPT'
]