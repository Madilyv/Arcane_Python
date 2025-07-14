# extensions/events/message/ticket_automation/core/__init__.py
"""
Core modules for ticket automation.
"""

from .state_manager import StateManager
from .questionnaire_manager import (
    trigger_questionnaire,
    send_interview_selection_prompt
)
from .question_flow import (
    send_next_question,
    is_awaiting_text_response
)

__all__ = [
    'StateManager',
    'trigger_questionnaire',
    'send_interview_selection_prompt',
    'send_next_question',
    'is_awaiting_text_response'
]