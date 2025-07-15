# extensions/events/message/ticket_automation/components/templates.py
"""
Message templates for consistent formatting across the automation.
These templates can be reused and customized as needed.
"""
from typing import Dict, List

# Interview selection template
INTERVIEW_SELECTION_TEMPLATE: dict[str, list[dict[str, str] | dict[str, str]] | str | None] = {
    "title": "## 🎯 **Choose Your Interview Type**",
    "content": (
        "Welcome to the recruitment process! You have two options:\n\n"
        "**🤖 Bot-Driven Interview**\n"
        "• Quick automated questions\n"
        "• Takes about 5-10 minutes\n"
        "• Get placed faster\n\n"
        "**💬 Speak with a Recruiter**\n"
        "• Personal 1-on-1 interview\n"
        "• More detailed discussion\n"
        "• Ask questions directly\n\n"
        "*Choose the option that works best for you!*"
    ),
    "footer": None,
    "buttons": [
        {
            "style": "PRIMARY",
            "label": "Bot-Driven Interview",
            "emoji": "🤖",
            "action": "select_bot_interview"
        },
        {
            "style": "SECONDARY",
            "label": "Speak with Recruiter",
            "emoji": "💬",
            "action": "select_recruiter_interview"
        }
    ]
}

# Completion template
COMPLETION_TEMPLATE = {
    "title": "🎉 **Questionnaire Complete!**",
    "content": (
        "Thank you for completing the recruitment questionnaire!\n\n"
        "Our team will review your responses and match you with the perfect clan.\n\n"
        "*You'll hear from us soon!*"
    ),
    "footer": None,
    "footer_image": "assets/Green_Footer.png"
}

# Error template
ERROR_TEMPLATE = {
    "title": "❌ **Error**",
    "content": "{error_message}",
    "footer": "Please try again or contact support",
    "footer_image": "assets/Red_Footer.png"
}

# Reminder template
REMINDER_TEMPLATE = {
    "title": "🔔 **Reminder**",
    "content": "{reminder_message}",
    "footer": "This reminder will auto-delete in {timeout} seconds",
    "footer_image": "assets/Gold_Footer.png"
}

# Success template
SUCCESS_TEMPLATE = {
    "title": "✅ **Success!**",
    "content": "{success_message}",
    "footer": None,
    "footer_image": "assets/Green_Footer.png"
}

# Halt automation template
HALT_TEMPLATE = {
    "title": "🛑 **Automation Paused**",
    "content": (
        "The automated process has been paused.\n\n"
        "**Reason:** {reason}\n\n"
        "A staff member will assist you shortly."
    ),
    "footer": "You can continue chatting in this channel",
    "footer_image": "assets/Red_Footer.png"
}