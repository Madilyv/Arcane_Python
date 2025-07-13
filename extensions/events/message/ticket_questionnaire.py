# extensions/events/message/ticket_questionnaire.py
"""
Ticket questionnaire automation system with AI-powered attack strategy processing.

Features:
- Interview process selection (Bot-driven vs Speak with Recruiter)
- AI-powered attack strategies analysis using Claude
- AI-powered clan expectations analysis using Claude
- Automation halt functionality for manual takeover
- Sequential question flow management
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hikari
import lightbulb

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from utils.constants import RED_ACCENT, GREEN_ACCENT, BLUE_ACCENT
from utils.mongo import MongoClient
from utils.emoji import emojis
from extensions.components import register_action
from utils.ai_prompts import ATTACK_STRATEGIES_PROMPT, CLAN_EXPECTATIONS_PROMPT

# Configuration
RECRUITMENT_STAFF_ROLE = 999140213953671188  # Note: Role ID as integer, not string
LOG_CHANNEL_ID = 1345589195695194113

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Global variables
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
loader = lightbulb.Loader()

# Export the trigger function
__all__ = ['trigger_questionnaire', 'send_interview_selection_prompt']

# Question definitions matching recruit questions command
QUESTIONNAIRE_QUESTIONS = {
    "attack_strategies": {
        "title": "## ⚔️ **Attack Strategy Breakdown**",
        "content": (
            "Help us understand your go-to attack strategies!\n\n"
            "{red_arrow} **Main Village strategies**\n"
            "{blank}{white_arrow} _e.g. Hybrid, Queen Charge w/ Hydra, Lalo_\n\n"
            "{red_arrow} **Clan Capital Attack Strategies**\n"
            "{blank}{white_arrow} _e.g. Super Miners w/ Freeze_\n\n"
            "{red_arrow} **Highest Clan Capital Hall level you've attacked**\n"
            "{blank}{white_arrow} _e.g. CH 8, CH 9, etc._\n\n"
            "*Your detailed breakdown helps us match you to the perfect clan!*"
        ),
        "next": "future_clan_expectations"
    },
    "future_clan_expectations": {
        "title": "## 🔮 **Future Clan Expectations**",
        "content": (
            "Help us tailor your clan experience! Please answer the following:\n\n"
            "{red_arrow} **What do you expect from your future clan?**\n"
            "{blank}{white_arrow} _(e.g., Active wars, good communication, strategic support.)_\n\n"
            "{red_arrow} **Minimum clan level you're looking for?**\n"
            "{blank}{white_arrow} _e.g. Level 5, Level 10_\n\n"
            "{red_arrow} **Minimum Clan Capital Hall level?**\n"
            "{blank}{white_arrow} _e.g. CH 8 or higher_\n\n"
            "{red_arrow} **CWL league preference?**\n"
            "{blank}{white_arrow} _e.g. Crystal, Masters, Champions_\n\n"
            "{red_arrow} **Preferred playstyle?**\n"
            "{blank}{white_arrow} Competitive\n"
            "{blank}{white_arrow} Casual\n"
            "{blank}{white_arrow} Zen _Type **What is Zen** to learn more._\n"
            "{blank}{white_arrow} FWA _Type **What is FWA** to learn more._\n\n"
            "*The more specific, the better we can match you!*"
        ),
        "next": "leaders_checking_you_out"
    },
    "leaders_checking_you_out": {
        "title": "## 👑 **Leaders Checking You Out**",
        "content": (
            "Heads up! Our clan leaders will be reviewing your profile:\n\n"
            "• **In-game profile** – Town Hall, hero levels, war stars\n"
            "• **Discord activity** – How you communicate and engage\n"
            "• **Application responses** – The info you've shared with us\n\n"
            "*Make sure your profile reflects your best! Leaders appreciate active, engaged members.*"
        ),
        "next": None  # This is the last question
    }
}


# Define trigger_questionnaire early to ensure it's available for import
async def trigger_questionnaire(channel_id: int, user_id: int):
    """Public function to trigger the questionnaire from other modules"""
    try:
        # Ensure global variables are initialized
        global mongo_client, bot_instance

        if not mongo_client or not bot_instance:
            from utils import bot_data
            mongo_client = bot_data.data.get("mongo")
            bot_instance = bot_data.data.get("bot")

        if not mongo_client or not bot_instance:
            print("[Questionnaire] Error: MongoDB or Bot instance not available")
            return

        print(f"[Questionnaire] Triggering questionnaire for channel {channel_id}, user {user_id}")
        await send_interview_selection_prompt(channel_id, user_id)
    except Exception as e:
        print(f"[Questionnaire] Error triggering questionnaire: {e}")
        import traceback
        traceback.print_exc()


# Question definitions matching recruit questions command
QUESTIONNAIRE_QUESTIONS = {
    "attack_strategies": {
        "title": "## ⚔️ **Attack Strategy Breakdown**",
        "content": (
            "Help us understand your go-to attack strategies!\n\n"
            "{red_arrow} **Main Village strategies**\n"
            "{blank}{white_arrow} _e.g. Hybrid, Queen Charge w/ Hydra, Lalo_\n\n"
            "{red_arrow} **Clan Capital Attack Strategies**\n"
            "{blank}{white_arrow} _e.g. Super Miners w/ Freeze_\n\n"
            "{red_arrow} **Highest Clan Capital Hall level you've attacked**\n"
            "{blank}{white_arrow} _e.g. CH 8, CH 9, etc._\n\n"
            "*Your detailed breakdown helps us match you to the perfect clan!*"
        ),
        "next": "future_clan_expectations"
    },
    "future_clan_expectations": {
        "title": "## 🔮 **Future Clan Expectations**",
        "content": (
            "Help us tailor your clan experience! Please answer the following:\n\n"
            "{red_arrow} **What do you expect from your future clan?**\n"
            "{blank}{white_arrow} _(e.g., Active wars, good communication, strategic support.)_\n\n"
            "{red_arrow} **Minimum clan level you're looking for?**\n"
            "{blank}{white_arrow} _e.g. Level 5, Level 10_\n\n"
            "{red_arrow} **Minimum Clan Capital Hall level?**\n"
            "{blank}{white_arrow} _e.g. CH 8 or higher_\n\n"
            "{red_arrow} **CWL league preference?**\n"
            "{blank}{white_arrow} _e.g. Crystal, Masters, Champions_\n\n"
            "*The more specific, the better we can match you!*"
        ),
        "next": "leaders_checking_you_out"
    },
    "leaders_checking_you_out": {
        "title": "## 👑 **Leaders Checking You Out**",
        "content": (
            "Heads up! Our clan leaders will be reviewing your profile:\n\n"
            "• **In-game profile** – Town Hall, hero levels, war stars\n"
            "• **Discord activity** – How you communicate and engage\n"
            "• **Application responses** – The info you've shared with us\n\n"
            "*Make sure your profile reflects your best! Leaders appreciate active, engaged members.*"
        ),
        "next": None  # This is the last question
    }
}


async def process_attack_strategies_with_ai(existing_summary: str, new_input: str) -> str:
    """Process attack strategies using Claude AI"""

    # The system prompt from your document
    system_prompt = ATTACK_STRATEGIES_PROMPT

    # Prepare the messages for Claude
    messages = [
        {
            "role": "user",
            "content": f"Existing summary:\n{existing_summary if existing_summary else 'None'}\n\nNew user input:\n{new_input}"
        }
    ]

    # Prepare request to Anthropic API
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1000,
        "messages": messages,
        "system": system_prompt
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    print(f"[Questionnaire] AI API error: {response.status}")
                    # Return existing summary on error
                    return existing_summary if existing_summary else ""
    except Exception as e:
        print(f"[Questionnaire] AI processing error: {e}")
        return existing_summary if existing_summary else ""


async def process_clan_expectations_with_ai(existing_summary: str, new_input: str) -> str:
    """Process clan expectations using Claude AI"""

    system_prompt = CLAN_EXPECTATIONS_PROMPT

    messages = [
        {
            "role": "user",
            "content": f"Existing summary:\n{existing_summary if existing_summary else 'None'}\n\nNew user input:\n{new_input}"
        }
    ]

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1000,
        "messages": messages,
        "system": system_prompt
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    print(f"[Questionnaire] AI API error: {response.status}")
                    return existing_summary if existing_summary else ""
    except Exception as e:
        print(f"[Questionnaire] AI processing error: {e}")
        return existing_summary if existing_summary else ""


async def create_attack_strategy_components(summary: str, title: str, show_done_button: bool = True) -> list:
    """Create components for displaying attack strategies with optional Done button"""

    # Replace placeholders in the summary
    formatted_summary = summary.replace("{red_arrow}", str(emojis.red_arrow_right))
    formatted_summary = formatted_summary.replace("{white_arrow}", str(emojis.white_arrow_right))
    formatted_summary = formatted_summary.replace("{blank}", str(emojis.blank))

    # If no summary yet, show instructions
    if not summary or summary.strip() == "":
        # Show the initial prompt with examples
        question_data = QUESTIONNAIRE_QUESTIONS["attack_strategies"]
        initial_content = question_data["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )
        display_content = initial_content
    else:
        # Once user starts typing, ONLY show their responses
        display_content = f"**Your strategies:**\n\n{formatted_summary}"

    components_list = [
        Text(content=title),
        Separator(divider=True),
        Text(content=display_content),
        Text(content="\n💡 _Type your strategies in chat and I'll add them automatically!_")
    ]

    if show_done_button:
        components_list.append(
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Done",
                        custom_id="attack_strategies_done:done",
                        emoji="✅"
                    )
                ]
            )
        )

    # Add footer image
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]

    return components


async def create_clan_expectations_components(summary: str, title: str, content: str,
                                              show_done_button: bool = True) -> list:
    """Create components for displaying clan expectations with optional Done button"""

    # Replace placeholders in the summary
    formatted_summary = summary.replace("{red_arrow}", str(emojis.red_arrow_right))
    formatted_summary = formatted_summary.replace("{white_arrow}", str(emojis.white_arrow_right))
    formatted_summary = formatted_summary.replace("{blank}", str(emojis.blank))

    # If no summary yet, show the original content with examples
    if not summary or summary.strip() == "":
        display_content = content
    else:
        # Once user starts typing, ONLY show their responses, not the examples
        display_content = f"**Your responses:**\n\n{formatted_summary}"

    components_list = [
        Text(content=title),
        Separator(divider=True),
        Text(content=display_content),
        Text(content="\n💡 _Type your preferences in chat and I'll categorize them automatically!_")
    ]

    if show_done_button:
        components_list.append(
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Done",
                        custom_id="clan_expectations_done:done",
                        emoji="✅"
                    )
                ]
            )
        )

    # Add footer image
    components_list.append(
        Media(items=[MediaItem(media="assets/Blue_Footer.png")])
    )

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=components_list
        )
    ]

    return components


async def send_attack_strategies(channel_id: int, user_id: int):
    """Send the attack strategies question with AI processing"""

    try:
        # Get ticket state
        ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        if not ticket_state:
            print(f"[Questionnaire] No ticket state found for channel {channel_id}")
            return

        question_key = "attack_strategies"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Set up state for collecting strategies
        update_result = await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.attack_summary": "",  # Initialize summary
                    "step_data.questionnaire.collecting_strategies": True  # Flag for continuous collection
                }
            }
        )

        print(
            f"[Questionnaire] Set collecting_strategies=True for channel {channel_id}, modified: {update_result.modified_count}")

        # Verify the update
        updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        collecting_flag = updated_state.get("step_data", {}).get("questionnaire", {}).get("collecting_strategies",
                                                                                          False)
        print(f"[Questionnaire] Verified collecting_strategies={collecting_flag} for channel {channel_id}")

        # Create initial components with empty summary
        components = await create_attack_strategy_components("", question_data["title"])

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(components=components)

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_{question_key}": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent attack strategies question with AI to channel {channel_id}, msg_id: {msg.id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending attack strategies: {e}")
        import traceback
        traceback.print_exc()


async def send_clan_expectations(channel_id: int, user_id: int):
    """Send the clan expectations question with AI processing"""

    try:
        ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        if not ticket_state:
            print(f"[Questionnaire] No ticket state found for channel {channel_id}")
            return

        question_key = "future_clan_expectations"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Format the content with emoji placeholders
        content = question_data["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

        # Set up state for collecting expectations
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.expectations_summary": "",  # Initialize summary
                    "step_data.questionnaire.collecting_expectations": True  # Flag for continuous collection
                }
            }
        )

        # Create initial components with empty summary but showing examples
        components = await create_clan_expectations_components(
            "",
            question_data["title"],
            content
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(components=components)

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_{question_key}": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent clan expectations question with AI to channel {channel_id}, msg_id: {msg.id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending clan expectations: {e}")
        import traceback
        traceback.print_exc()


async def send_interview_selection_prompt(channel_id: int, user_id: int):
    """Send the interview process selection message"""
    try:
        # Create the message components
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"## <@{user_id}>"),
                    Separator(divider=True),
                    Text(content=(
                        "## 💼 **Choose Your Interview Process**\n\n"
                        "Our recruitment process offers two options for you to choose from:\n\n"
                        "**1️⃣ Bot-Driven Interview:** A step-by-step automated process.\n"
                        "**2️⃣ One-on-One Interview:** Speak directly with a Recruiter.\n\n"
                        "Both options cover the same content—pick whichever works best for you!\n\n"
                        "*Your choice, your journey!*"
                    )),
                    ActionRow(
                        components=[
                            Button(
                                style=hikari.ButtonStyle.PRIMARY,
                                label="Bot-Driven Interview",
                                custom_id=f"select_bot_interview:{channel_id}_{user_id}",
                                emoji="🤖"
                            ),
                            Button(
                                style=hikari.ButtonStyle.SECONDARY,
                                label="Speak with Recruiter",
                                custom_id=f"select_recruiter_interview:{channel_id}_{user_id}",
                                emoji="💬"
                            )
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(components=components)

        print(f"[Questionnaire] Sent interview selection prompt to channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending interview selection: {e}")
        import traceback
        traceback.print_exc()


# Handler for Bot-Driven Interview selection
@register_action("select_bot_interview", no_return=True)
async def handle_bot_interview_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user selects bot-driven interview"""

    parts = action_id.split("_")
    channel_id = parts[0]
    user_id = parts[1]

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This is not your recruitment process.",
            ephemeral=True
        )
        return

    # Update the message to show selection
    confirmation_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ✅ **Bot-Driven Interview Selected!**"),
                Text(content=(
                    "Great choice! I'll guide you through the recruitment process step by step.\n"
                    "Let's start with understanding your attack strategies..."
                )),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await ctx.interaction.edit_initial_response(components=confirmation_components)

    # Update MongoDB
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.interview_type": "bot_driven",
                "step_data.questionnaire.started": True
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "selected_bot_interview",
                    "details": {"user_id": user_id}
                }
            }
        }
    )

    # Wait a moment before sending the attack strategies question
    await asyncio.sleep(2)

    # Send first question (attack strategies) with AI
    await send_attack_strategies(int(channel_id), int(user_id))


# Handler for the Done button on attack strategies
@register_action("attack_strategies_done", no_return=True)
async def handle_attack_strategies_done(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user clicks Done on attack strategies"""

    channel_id = ctx.channel_id
    user_id = ctx.user.id

    # Verify this is the correct user
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not ticket_state:
        await ctx.respond("❌ Ticket state not found.", ephemeral=True)
        return

    # Check multiple possible locations for user ID and handle type conversion
    stored_user_id = (
            ticket_state.get("discord_id") or
            ticket_state.get("ticket_info", {}).get("user_id") or
            ticket_state.get("user_id")
    )

    # Convert to int for comparison if it's stored as string
    if stored_user_id:
        try:
            stored_user_id = int(stored_user_id)
        except (ValueError, TypeError):
            print(f"[Questionnaire] Error converting user_id: {stored_user_id}")
            pass

    if not stored_user_id or user_id != stored_user_id:
        print(f"[Questionnaire] User ID mismatch: {user_id} != {stored_user_id}")
        await ctx.respond("❌ You cannot interact with this ticket.", ephemeral=True)
        return

    # Stop collecting strategies
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.collecting_strategies": False,
                "step_data.questionnaire.awaiting_response": False
            }
        }
    )

    # Get the current attack summary to display
    current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

    # Create the same components but without the Done button
    final_components = await create_attack_strategy_components(
        current_summary,
        QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
        show_done_button=False  # Add parameter to hide button
    )

    # Update the message to remove the Done button (interaction already deferred by component_handler)
    await ctx.interaction.edit_initial_response(components=final_components)

    # Wait and move to next question
    await asyncio.sleep(2)

    # Move to next question
    next_question = QUESTIONNAIRE_QUESTIONS["attack_strategies"]["next"]
    if next_question:
        await send_questionnaire_question(channel_id, user_id, next_question)

    print(f"[Questionnaire] User {user_id} completed attack strategies")


# Handler for the Done button on clan expectations
@register_action("clan_expectations_done", no_return=True)
async def handle_clan_expectations_done(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user clicks Done on clan expectations"""

    channel_id = ctx.channel_id
    user_id = ctx.user.id

    # Verify this is the correct user
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not ticket_state:
        await ctx.respond("❌ Ticket state not found.", ephemeral=True)
        return

    stored_user_id = (
            ticket_state.get("discord_id") or
            ticket_state.get("ticket_info", {}).get("user_id") or
            ticket_state.get("user_id")
    )

    if stored_user_id:
        try:
            stored_user_id = int(stored_user_id)
        except (ValueError, TypeError):
            print(f"[Questionnaire] Error converting user_id: {stored_user_id}")
            pass

    if not stored_user_id or user_id != stored_user_id:
        await ctx.respond("❌ You cannot interact with this ticket.", ephemeral=True)
        return

    # Stop collecting expectations
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.collecting_expectations": False,
                "step_data.questionnaire.awaiting_response": False
            }
        }
    )

    # Get the current expectations summary to display
    current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("expectations_summary", "")

    question_data = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]
    content = question_data["content"].format(
        red_arrow=str(emojis.red_arrow_right),
        white_arrow=str(emojis.white_arrow_right),
        blank=str(emojis.blank)
    )

    # Create the same components but without the Done button
    final_components = await create_clan_expectations_components(
        current_summary,
        question_data["title"],
        content,
        show_done_button=False
    )

    # Update the message to remove the Done button
    await ctx.interaction.edit_initial_response(components=final_components)

    # Wait and move to next question
    await asyncio.sleep(2)

    # Move to next question
    next_question = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]["next"]
    if next_question:
        await send_questionnaire_question(channel_id, user_id, next_question)

    print(f"[Questionnaire] User {user_id} completed clan expectations")


async def send_questionnaire_question(channel_id: int, user_id: int, question_key: str):
    """Send a specific questionnaire question"""
    try:
        # Special handling for attack strategies with AI
        if question_key == "attack_strategies":
            await send_attack_strategies(channel_id, user_id)
            return

        # Special handling for clan expectations with AI
        if question_key == "future_clan_expectations":
            await send_clan_expectations(channel_id, user_id)
            return

        question = QUESTIONNAIRE_QUESTIONS.get(question_key)
        if not question:
            print(f"[Questionnaire] Unknown question key: {question_key}")
            return

        # Format the content with emoji placeholders
        content = question["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

        # Build components
        components_list = [
            Text(content=f"<@{user_id}>"),
            Separator(divider=True),
            Text(content=f"{question['title']}\n\n{content}")
        ]

        # Add GIF if specified
        if question.get("has_gif") and question.get("gif_url"):
            components_list.append(
                Media(items=[MediaItem(media=question["gif_url"])])
            )
        else:
            components_list.append(
                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            )

        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=components_list
            )
        ]

        # Update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True
                }
            }
        )

        # Send the message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(components=components)

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_{question_key}": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent question {question_key} to channel {channel_id}")

        # If this is the last question, wait and then send completion message
        if question.get("next") is None:
            await asyncio.sleep(3)  # Give user time to read
            await send_questionnaire_completion(channel_id, user_id)

    except Exception as e:
        print(f"[Questionnaire] Error sending question {question_key}: {e}")
        import traceback
        traceback.print_exc()


async def send_questionnaire_completion(channel_id: int, user_id: int):
    """Send completion message when questionnaire is finished"""
    try:
        # Update ticket state to mark questionnaire as complete
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.completed": True,
                    "step_data.questionnaire.awaiting_response": False,
                    "automation_state.current_step": "questionnaire_complete"
                }
            }
        )

        # Create completion message
        completion_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content=f"## ✅ **Interview Complete!**"),
                    Text(content=(
                        "Thank you for completing the recruitment questionnaire!\n\n"
                        "Our team will review your responses and match you with the perfect clan.\n\n"
                        "*You'll hear from us soon!*"
                    )),
                    Media(items=[MediaItem(media="assets/Green_Footer.png")])
                ]
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(components=completion_components)

        print(f"[Questionnaire] Sent completion message for user {user_id} in channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending completion message: {e}")
        import traceback
        traceback.print_exc()


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for questionnaire responses in ticket channels"""

    # Skip bot messages
    if event.is_bot:
        return

    if not mongo_client or not bot_instance:
        return

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if not ticket_state:
        return

    # Check if we're collecting attack strategies with AI
    if (ticket_state.get("step_data", {}).get("questionnaire", {}).get("collecting_strategies", False)):

        # Check if message is from the right user - try multiple locations and handle type conversion
        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        # Convert to int for comparison if it's stored as string
        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                print(f"[Questionnaire] Error converting user_id: {expected_user_id}")
                expected_user_id = None

        if expected_user_id and event.author_id != expected_user_id:
            print(f"[Questionnaire] Ignoring message from wrong user: {event.author_id} != {expected_user_id}")
            return

        print(f"[Questionnaire] Processing attack strategy from user {event.author_id}: {event.content}")

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

        # Process with AI
        new_summary = await process_attack_strategies_with_ai(current_summary, event.content)

        # Update database with new summary
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(event.channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.attack_summary": new_summary,
                    "step_data.questionnaire.responses.attack_strategies": new_summary
                }
            }
        )

        # Update the message with new components
        msg_id = ticket_state.get("messages", {}).get("questionnaire_attack_strategies")
        if msg_id:
            try:
                components = await create_attack_strategy_components(
                    new_summary,
                    QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"]
                )
                await bot_instance.rest.edit_message(event.channel_id, int(msg_id), components=components)
                print(f"[Questionnaire] Updated attack strategy display")
            except Exception as e:
                print(f"[Questionnaire] Error updating attack strategy message: {e}")
                import traceback
                traceback.print_exc()

        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass  # Ignore if we can't delete

        return  # IMPORTANT: Exit here, don't process as normal response

    # Check if we're collecting clan expectations with AI
    if (ticket_state.get("step_data", {}).get("questionnaire", {}).get("collecting_expectations", False)):

        # Check if message is from the right user
        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                print(f"[Questionnaire] Error converting user_id: {expected_user_id}")
                expected_user_id = None

        if expected_user_id and event.author_id != expected_user_id:
            return

        print(f"[Questionnaire] Processing clan expectation from user {event.author_id}: {event.content}")

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("expectations_summary", "")

        # Process with AI
        new_summary = await process_clan_expectations_with_ai(current_summary, event.content)

        # Update database with new summary
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(event.channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.expectations_summary": new_summary,
                    "step_data.questionnaire.responses.future_clan_expectations": new_summary
                }
            }
        )

        # Update the message with new components
        msg_id = ticket_state.get("messages", {}).get("questionnaire_future_clan_expectations")
        if msg_id:
            try:
                question_data = QUESTIONNAIRE_QUESTIONS["future_clan_expectations"]
                content = question_data["content"].format(
                    red_arrow=str(emojis.red_arrow_right),
                    white_arrow=str(emojis.white_arrow_right),
                    blank=str(emojis.blank)
                )

                components = await create_clan_expectations_components(
                    new_summary,
                    question_data["title"],
                    content
                )
                await bot_instance.rest.edit_message(event.channel_id, int(msg_id), components=components)
                print(f"[Questionnaire] Updated clan expectations display")
            except Exception as e:
                print(f"[Questionnaire] Error updating clan expectations message: {e}")
                import traceback
                traceback.print_exc()

        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass

        return  # Exit here, don't process as normal response

    # Check if we're in questionnaire step and awaiting response
    if (ticket_state.get("automation_state", {}).get("current_step") != "questionnaire" or
            not ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_response") or
            ticket_state.get("automation_state", {}).get("status") == "halted"):
        return

    # Verify message is from ticket creator (double check)
    if "ticket_info" in ticket_state and event.author_id != int(ticket_state["ticket_info"]["user_id"]):
        return

    current_question = ticket_state["step_data"]["questionnaire"].get("current_question")

    # [Rest of the questionnaire response handling code remains the same...]


# Initialize when bot starts
@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent):
    global mongo_client, bot_instance

    from utils import bot_data
    mongo_client = bot_data.data.get("mongo")
    bot_instance = bot_data.data.get("bot")

    if mongo_client and bot_instance:
        print("Questionnaire automation system with AI initialized")