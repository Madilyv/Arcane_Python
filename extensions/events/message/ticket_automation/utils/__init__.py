# extensions/events/message/ticket_automation/utils/__init__.py
"""Utility functions and constants for ticket automation"""

from .constants import (
    QUESTIONNAIRE_QUESTIONS,
    RECRUITMENT_STAFF_ROLE,
    LOG_CHANNEL_ID,
    REMINDER_DELETE_TIMEOUT,
    REMINDER_TIMEOUT,
    TIMEZONE_CONFIRMATION_TIMEOUT
)

from .helpers import (
    format_user_mention,
    format_channel_mention,
    calculate_time_difference,
    clean_message_content
)

from .validators import (
    validate_user_id,
    validate_channel_id,
    is_valid_timezone,
    is_automation_active
)

__all__ = [
    'QUESTIONNAIRE_QUESTIONS',
    'RECRUITMENT_STAFF_ROLE',
    'LOG_CHANNEL_ID',
    'REMINDER_DELETE_TIMEOUT',
    'REMINDER_TIMEOUT',
    'TIMEZONE_CONFIRMATION_TIMEOUT',
    'format_user_mention',
    'format_channel_mention',
    'calculate_time_difference',
    'clean_message_content',
    'validate_user_id',
    'validate_channel_id',
    'is_valid_timezone',
    'is_automation_active'
]