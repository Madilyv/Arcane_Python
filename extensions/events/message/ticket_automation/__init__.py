# extensions/events/message/ticket_automation/__init__.py
"""
Ticket automation package initialization.
Exports main functions for external use.
"""

from .core.questionnaire_manager import (
    trigger_questionnaire,
    send_interview_selection_prompt,
    halt_automation,
    resume_automation
)

from .core.question_flow import (
    send_questionnaire_question,
    get_next_question,
    is_final_question
)

from .handlers.interview_selection import (
    handle_bot_interview_selection,
    handle_recruiter_interview_selection
)

__all__ = [
    'trigger_questionnaire',
    'send_interview_selection_prompt',
    'halt_automation',
    'resume_automation',
    'send_questionnaire_question',
    'get_next_question',
    'is_final_question',
    'handle_bot_interview_selection',
    'handle_recruiter_interview_selection'
]