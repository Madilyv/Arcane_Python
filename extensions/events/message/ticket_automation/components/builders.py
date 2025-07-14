# extensions/events/message/ticket_automation/components/builders.py
"""
Reusable component builders for creating consistent UI elements.
These can be used across ticket automation and FWA automation.
"""

from typing import Optional, Dict, Any, List
import hikari

from hikari.impl import (
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

    # Handle buttons if present in template - Components V2 style with Sections
    if template.get("buttons"):
        # For two buttons side by side, we create two sections
        if len(template["buttons"]) == 2:
            # First button
            button1_data = template["buttons"][0]
            style1 = getattr(hikari.ButtonStyle, button1_data["style"])
            custom_id1 = f"{button1_data['action']}:{channel_id}_{user_id}"

            button1 = Button(
                style=style1,
                label=button1_data["label"],
                custom_id=custom_id1,
            )
            if button1_data.get("emoji"):
                button1.set_emoji(button1_data["emoji"])

            # Second button
            button2_data = template["buttons"][1]
            style2 = getattr(hikari.ButtonStyle, button2_data["style"])
            custom_id2 = f"{button2_data['action']}:{channel_id}_{user_id}"

            button2 = Button(
                style=style2,
                label=button2_data["label"],
                custom_id=custom_id2,
            )
            if button2_data.get("emoji"):
                button2.set_emoji(button2_data["emoji"])

            # Create sections for the buttons
            components_list.append(
                Section(
                    components=[
                        Text(content="Option 1: Speak with Recruiter")
                    ],
                    accessory=button2
                )
            )
            components_list.append(
                Section(
                    components=[
                        Text(content="Option 2: Bot-Driven Interview")
                    ],
                    accessory=button1
                )
            )
        else:
            # For single button or multiple buttons, create a section for each
            for i, button_data in enumerate(template["buttons"]):
                style = getattr(hikari.ButtonStyle, button_data["style"])
                custom_id = f"{button_data['action']}:{channel_id}_{user_id}"

                button = Button(
                    style=style,
                    label=button_data["label"],
                    custom_id=custom_id,
                )
                if button_data.get("emoji"):
                    button.set_emoji(button_data["emoji"])

                # Create section with descriptive text and button
                components_list.append(
                    Section(
                        components=[
                            Text(content=f"Option {i + 1}")
                        ],
                        accessory=button
                    )
                )

    # Add media (GIF or image)
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
        user_id: Optional[int] = None,
        **kwargs
) -> List[Any]:
    """Create components for attack strategy display with AI summary"""

    # Extract channel_id from kwargs
    channel_id = kwargs.get('channel_id')

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

    # If no summary yet, show the full detailed prompt with examples
    if not summary or summary.strip() == "":
        # Show the full formatted content with all the details
        detailed_content = (
            "Help us understand your go-to attack strategies!\n\n"
            f"{str(emojis.red_arrow_right)} **Main Village strategies**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. Hybrid, Queen Charge w/ Hydra, Lalo_\n\n"
            f"{str(emojis.red_arrow_right)} **Clan Capital Attack Strategies**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. Super Miners w/ Freeze_\n\n"
            f"{str(emojis.red_arrow_right)} **Highest Clan Capital Hall level you've attacked**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. CH 8, CH 9, etc._\n\n"
            "*Your detailed breakdown helps us match you to the perfect clan!*"
        )
        components_list.append(Text(content=detailed_content))

        # Add instruction at the bottom
        components_list.append(
            Text(content="\n💡 _Type your strategies below and I'll organize them for you. Click Done when finished._"))
    else:
        # Once user starts typing, show their organized summary
        components_list.append(
            Text(
                content="📝 **Tell us about your attack strategies!**\n\n*Continue typing or click Done when finished.*")
        )

        # Add current summary
        components_list.append(Separator(divider=True))
        components_list.append(
            Section(
                components=[
                    Text(content="**📋 Your Attack Strategies:**"),
                    Text(content=formatted_summary)
                ]
            )
        )

    # Add footer image
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    # Add Done button if requested - Must be in a Section
    if show_done_button:
        # Use proper custom_id format with channel_id and user_id
        custom_id = f"attack_strategies_done:{channel_id}_{user_id}" if channel_id and user_id else "attack_strategies_done:done"

        done_button = Button(
            style=hikari.ButtonStyle.SUCCESS,
            label="Done",
            custom_id=custom_id,
        )
        done_button.set_emoji("✅")

        # Add button in a Section
        components_list.append(
            Section(
                components=[
                    Text(content="Ready to continue? Click the button when you've finished entering your strategies.")
                ],
                accessory=done_button
            )
        )

    # Create and return container with all components inside
    return [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]


async def create_clan_expectations_components(
        summary: str,
        title: str,
        content: str,
        show_done_button: bool = True,
        include_user_ping: bool = False,
        user_id: Optional[int] = None,
        **kwargs
) -> List[Any]:
    """Create components for clan expectations display with AI summary"""

    # Extract channel_id from kwargs
    channel_id = kwargs.get('channel_id')

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

    # If no summary yet, show the full detailed prompt with all questions
    if not summary or summary.strip() == "":
        # Show the full formatted content with all the detailed questions
        detailed_content = (
            "Help us tailor your clan experience! Please answer the following:\n\n"
            f"{str(emojis.red_arrow_right)} **What do you expect from your future clan?**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _(e.g., Active wars, good communication, strategic support.)_\n\n"
            f"{str(emojis.red_arrow_right)} **Minimum clan level you're looking for?**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. Level 5, Level 10_\n\n"
            f"{str(emojis.red_arrow_right)} **Minimum Clan Capital Hall level?**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. CH 8 or higher_\n\n"
            f"{str(emojis.red_arrow_right)} **CWL league preference?**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} _e.g. Crystal, Masters, Champions_\n\n"
            f"{str(emojis.red_arrow_right)} **Preferred playstyle?**\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} Competitive\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} Casual\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} Zen _Type **What is Zen** to learn more._\n"
            f"{str(emojis.blank)}{str(emojis.white_arrow_right)} FWA _Type **What is FWA** to learn more._\n\n"
            "*The more specific, the better we can match you!*"
        )
        components_list.append(Text(content=detailed_content))

        # Add instruction at the bottom
        components_list.append(Text(
            content="\n💡 _Type your preferences below and I'll categorize them automatically! Click Done when finished._"))
    else:
        # Once user starts typing, show their organized summary
        components_list.append(
            Text(
                content="📝 **Share what you're looking for in a clan!**\n\n*Continue typing or click Done when finished.*")
        )

        # Add current summary
        components_list.append(Separator(divider=True))
        components_list.append(
            Section(
                components=[
                    Text(content="**📋 Your Clan Expectations:**"),
                    Text(content=formatted_summary)
                ]
            )
        )

    # Add footer image
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    # Add Done button if requested - Must be in a Section
    if show_done_button:
        # Use proper custom_id format with channel_id and user_id
        custom_id = f"clan_expectations_done:{channel_id}_{user_id}" if channel_id and user_id else "clan_expectations_done:done"

        done_button = Button(
            style=hikari.ButtonStyle.SUCCESS,
            label="Done",
            custom_id=custom_id,
        )
        done_button.set_emoji("✅")

        # Add button in a Section
        components_list.append(
            Section(
                components=[
                    Text(content="Finished sharing your expectations? Click Done to proceed to the next question.")
                ],
                accessory=done_button
            )
        )

    # Create and return container with all components inside
    return [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]