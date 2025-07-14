# extensions/events/message/ticket_automation/utils/validators.py
"""
Validation functions for ticket automation.
Ensures data integrity and prevents errors.
"""

import re
from typing import Optional, Union
from datetime import datetime
import pytz


def validate_user_id(user_id: Union[int, str]) -> Optional[int]:
    """
    Validate and convert a user ID to int.

    Args:
        user_id: User ID as int or string

    Returns:
        Valid user ID as int, or None if invalid
    """
    try:
        user_id_int = int(user_id)
        # Discord user IDs are positive integers
        if user_id_int > 0:
            return user_id_int
    except (ValueError, TypeError):
        pass
    return None


def validate_channel_id(channel_id: Union[int, str]) -> Optional[int]:
    """
    Validate and convert a channel ID to int.

    Args:
        channel_id: Channel ID as int or string

    Returns:
        Valid channel ID as int, or None if invalid
    """
    try:
        channel_id_int = int(channel_id)
        # Discord channel IDs are positive integers
        if channel_id_int > 0:
            return channel_id_int
    except (ValueError, TypeError):
        pass
    return None


def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if a string is a valid timezone.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        True if valid timezone, False otherwise
    """
    # Check common timezone abbreviations
    common_timezones = {
        'EST', 'EDT', 'CST', 'CDT', 'MST', 'MDT', 'PST', 'PDT',
        'GMT', 'UTC', 'BST', 'CET', 'CEST', 'IST', 'JST', 'AEST', 'AEDT'
    }

    if timezone_str.upper() in common_timezones:
        return True

    # Check UTC offset format (e.g., UTC+5, UTC-8)
    if re.match(r'^UTC[+-]\d{1,2}$', timezone_str.upper()):
        return True

    # Check if it's a valid pytz timezone
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        pass

    # Check if it's a major city that pytz might recognize
    # Try with common timezone database formats
    for prefix in ['', 'America/', 'Europe/', 'Asia/', 'Australia/', 'Africa/']:
        try:
            pytz.timezone(prefix + timezone_str.replace(' ', '_'))
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            continue

    return False


def is_automation_active(ticket_state: dict) -> bool:
    """
    Check if automation is active for a ticket.

    Args:
        ticket_state: Ticket state dictionary from database

    Returns:
        True if automation is active, False otherwise
    """
    if not ticket_state:
        return False

    automation_state = ticket_state.get("automation_state", {})
    status = automation_state.get("status", "")

    return status == "active"


def validate_button_action_id(action_id: str, expected_prefix: str) -> Optional[dict]:
    """
    Validate and parse a button action ID.

    Args:
        action_id: The action ID from the button
        expected_prefix: Expected prefix for the action

    Returns:
        Dictionary with parsed values or None if invalid
    """
    if not action_id.startswith(expected_prefix):
        return None

    parts = action_id.split("_")
    if len(parts) < 3:  # Minimum: prefix_action_data
        return None

    return {
        "prefix": expected_prefix,
        "parts": parts,
        "full_id": action_id
    }


def validate_message_content(content: str, max_length: int = 2000) -> tuple[bool, Optional[str]]:
    """
    Validate message content for Discord limits.

    Args:
        content: Message content to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return False, "Message content cannot be empty"

    if len(content) > max_length:
        return False, f"Message content exceeds {max_length} characters"

    # Check for only whitespace
    if not content.strip():
        return False, "Message content cannot be only whitespace"

    return True, None


def validate_emoji(emoji_str: str) -> bool:
    """
    Validate if a string is a valid emoji or Discord custom emoji.

    Args:
        emoji_str: Emoji string to validate

    Returns:
        True if valid emoji, False otherwise
    """
    # Check for custom Discord emoji format <:name:id>
    if re.match(r'^<a?:\w+:\d+>$', emoji_str):
        return True

    # Check for Unicode emoji (simplified check)
    # This is a basic check - comprehensive emoji validation is complex
    if len(emoji_str) <= 4 and any(ord(char) > 127 for char in emoji_str):
        return True

    return False


def validate_questionnaire_response(question_type: str, response: str) -> tuple[bool, Optional[str]]:
    """
    Validate a questionnaire response based on question type.

    Args:
        question_type: Type of question
        response: User's response

    Returns:
        Tuple of (is_valid, error_message)
    """
    if question_type == "text_response":
        if not response or not response.strip():
            return False, "Response cannot be empty"
        if len(response) > 1000:
            return False, "Response is too long (max 1000 characters)"
        return True, None

    elif question_type == "expected_response":
        # For questions expecting specific responses like "done"
        expected_responses = ["done", "yes", "no", "skip"]
        if response.lower().strip() not in expected_responses:
            return False, f"Expected one of: {', '.join(expected_responses)}"
        return True, None

    elif question_type == "ai_continuous":
        # AI-processed responses have more lenient validation
        if len(response) > 2000:
            return False, "Response is too long (max 2000 characters)"
        return True, None

    # Default validation
    return True, None