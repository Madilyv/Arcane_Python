# extensions/events/message/ticket_automation/components/builders.py
"""
Reusable component builders for creating consistent UI elements.
These can be used across ticket automation and FWA automation.
"""

from typing import Optional, Dict, Any, List
import hikari

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    SectionComponentBuilder as Section,
)

from utils.constants import BLUE_ACCENT
from utils.emoji import emojis


def create_container_component(
        template: Dict[str, Any],
        accent_color: int = BLUE_ACCENT,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None
) -> List[Container]:
    """
    Create a container component from a template.

    Args:
        template: Dictionary with title, content, footer, gif_url, etc.
        accent_color: Color for the container accent
        user_id: Optional user ID for mentions
        channel_id: Optional channel ID for context
    """
    components_list = []

    # Add user mention if provided
    if user_id:
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

    # Add title if provided
    if template.get("title"):
        components_list.append(Text(content=template["title"]))

    # Add separator after title
    if template.get("title") and template.get("content"):
        components_list.append(Separator(divider=True))

    # Add content
    if template.get("content"):
        components_list.append(Text(content=template["content"]))

    # Add footer if provided
    if template.get("footer"):
        components_list.append(Text(content=f"-# {template['footer']}"))

    # Handle buttons if present in template - ADD TO COMPONENTS LIST
    if template.get("buttons"):
        row = ActionRow()
        for button_data in template["buttons"]:
            # Get button style
            style = getattr(hikari.ButtonStyle, button_data["style"])

            # Build custom_id with channel and user info
            custom_id = f"{button_data['action']}:{channel_id}_{user_id}"

            # Create and add button with all parameters
            row.add_interactive_button(
                style,  # Positional argument
                custom_id,  # Positional argument
                label=button_data["label"],  # Keyword argument
                emoji=button_data.get("emoji")  # Keyword argument
            )

        # Add the ActionRow to the components list BEFORE media
        components_list.append(row)

    # Add media (GIF or image) - AFTER buttons
    if template.get("gif_url"):
        components_list.append(
            Media(items=[MediaItem(media=template["gif_url"])])
        )
    elif template.get("image_url"):
        components_list.append(
            Media(items=[MediaItem(media=template["image_url"])])
        )
    else:
        # Default footer image
        footer_image = template.get("footer_image", "assets/Blue_Footer.png")
        components_list.append(
            Media(items=[MediaItem(media=footer_image)])
        )

    # Create and return the container with ALL components inside
    return [
        Container(
            accent_color=accent_color,
            components=components_list
        )
    ]


def create_question_component(
        question_data: Dict[str, Any],
        user_id: Optional[int] = None
) -> List[Container]:
    """Create components for a standard questionnaire question"""

    # Format content with emoji placeholders
    content = question_data.get("content", "")
    if "{red_arrow}" in content:
        content = content.format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

    template = {
        "title": question_data.get("title"),
        "content": content,
        "footer": question_data.get("footer", "Type your response below"),
        "gif_url": question_data.get("gif_url") if question_data.get("has_gif") else None
    }

    return create_container_component(template, user_id=user_id)


def create_button(
        style: hikari.ButtonStyle,
        label: str,
        custom_id: str,
        emoji: Optional[str] = None,
        disabled: bool = False
) -> Button:
    """Create a button with consistent styling"""

    button = Button(
        style=style,
        label=label,
        custom_id=custom_id,
        is_disabled=disabled
    )

    if emoji:
        button.set_emoji(emoji)

    return button


async def create_attack_strategy_components(
        summary: str,
        title: str,
        show_done_button: bool = True,
        include_user_ping: bool = False,
        user_id: Optional[int] = None
) -> List[Any]:
    """Create components for attack strategy display with AI summary"""

    # Format summary with emojis
    formatted_summary = summary.replace("{red_arrow}", str(emojis.red_arrow_right))
    formatted_summary = formatted_summary.replace("{white_arrow}", str(emojis.white_arrow_right))
    formatted_summary = formatted_summary.replace("{blank}", str(emojis.blank))

    components_list = []

    # Add user ping if requested
    if include_user_ping and user_id:
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

    # Add title
    components_list.append(Text(content=title))
    components_list.append(Separator(divider=True))

    # Add instruction text
    instruction = (
        "📝 **Tell us about your attack strategies!**\n\n"
        "*Type your strategies below and I'll organize them for you.*\n"
        "*Click Done when finished.*"
    )
    components_list.append(Text(content=instruction))

    # Add current summary if exists
    if summary:
        components_list.append(Separator(divider=True))
        components_list.append(
            Section(
                components=[
                    Text(content="**📋 Your Attack Strategies:**"),
                    Text(content=formatted_summary)
                ]
            )
        )

    # Add footer
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    # Create container
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]

    # Add Done button if requested
    if show_done_button:
        row = ActionRow()
        row.add_interactive_button(
            style=hikari.ButtonStyle.SUCCESS,
            label="Done",
            custom_id="attack_strategies_done:done",
            emoji="✅"
        )
        components.append(row)

    return components


async def create_clan_expectations_components(
        summary: str,
        title: str,
        content: str,
        show_done_button: bool = True,
        include_user_ping: bool = False,
        user_id: Optional[int] = None
) -> List[Any]:
    """Create components for clan expectations display with AI summary"""

    components_list = []

    # Add user ping if requested
    if include_user_ping and user_id:
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

    # Add title
    components_list.append(Text(content=title))
    components_list.append(Separator(divider=True))

    # Add content with examples if no summary yet
    if not summary:
        components_list.append(Text(content=content))
    else:
        # Show instruction and summary
        components_list.append(
            Text(content="📝 **Share what you're looking for in a clan!**\n\n*Type below and click Done when finished.*")
        )
        components_list.append(Separator(divider=True))
        components_list.append(
            Section(
                components=[
                    Text(content="**📋 Your Clan Expectations:**"),
                    Text(content=summary)
                ]
            )
        )

    # Add footer
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    # Create container
    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]

    # Add Done button if requested
    if show_done_button:
        row = ActionRow()
        row.add_interactive_button(
            style=hikari.ButtonStyle.SUCCESS,
            label="Done",
            custom_id="clan_expectations_done:done",
            emoji="✅"
        )
        components.append(row)

    return components