# extensions/events/message/ticket_automation/components/styles.py
"""
Consistent styling definitions for components.
Ensures uniform appearance across all automation messages.
"""

from utils.constants import (
    RED_ACCENT,
    GREEN_ACCENT,
    BLUE_ACCENT,
    GOLD_ACCENT,
    MAGENTA_ACCENT
)

# Button style mappings
BUTTON_STYLES = {
    "primary": "PRIMARY",
    "secondary": "SECONDARY",
    "success": "SUCCESS",
    "danger": "DANGER",
    "link": "LINK"
}

# Color mappings for different message types
MESSAGE_COLORS = {
    "info": BLUE_ACCENT,
    "success": GREEN_ACCENT,
    "warning": GOLD_ACCENT,
    "error": RED_ACCENT,
    "special": MAGENTA_ACCENT
}

# Footer image mappings
FOOTER_IMAGES = {
    "default": "assets/Blue_Footer.png",
    "success": "assets/Green_Footer.png",
    "error": "assets/Red_Footer.png",
    "warning": "assets/Gold_Footer.png",
    "special": "assets/Magenta_Footer.png"
}

# Emoji mappings for consistent usage
EMOJI_MAP = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "question": "❓",
    "time": "⏰",
    "user": "👤",
    "bot": "🤖",
    "chat": "💬",
    "document": "📝",
    "clipboard": "📋",
    "target": "🎯",
    "sword": "⚔️",
    "shield": "🛡️",
    "crown": "👑",
    "star": "⭐",
    "fire": "🔥",
    "lightning": "⚡",
    "rocket": "🚀",
    "party": "🎉",
    "eyes": "👀",
    "bell": "🔔",
    "stop": "🛑",
    "play": "▶️",
    "pause": "⏸️",
    "check": "✔️",
    "cross": "✖️"
}

# Text formatting helpers
def format_bold(text: str) -> str:
    """Format text as bold"""
    return f"**{text}**"

def format_italic(text: str) -> str:
    """Format text as italic"""
    return f"*{text}*"

def format_code(text: str) -> str:
    """Format text as inline code"""
    return f"`{text}`"

def format_codeblock(text: str, language: str = "") -> str:
    """Format text as code block"""
    return f"```{language}\n{text}\n```"

def format_header(text: str, level: int = 2) -> str:
    """Format text as header (level 1-6)"""
    return f"{'#' * level} {text}"

def format_quote(text: str) -> str:
    """Format text as quote"""
    return f"> {text}"

def format_list_item(text: str, bullet: str = "•") -> str:
    """Format text as list item"""
    return f"{bullet} {text}"