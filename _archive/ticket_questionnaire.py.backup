# extensions/events/message/ticket_questionnaire.py
"""
Ticket questionnaire automation system with AI-powered attack strategy processing.

Features:
- Interview process selection (Bot-driven vs Speak with Recruiter)
- AI-powered attack strategies analysis using Claude
- AI-powered clan expectations analysis using Claude
- Discord skills verification (reactions and mentions)
- Age bracket selection with GIF responses
- Timezone collection
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
    SectionComponentBuilder as Section,
    LinkButtonBuilder as LinkButton,
)

from utils.constants import RED_ACCENT, GREEN_ACCENT, BLUE_ACCENT, GOLD_ACCENT
from utils.mongo import MongoClient
from utils.emoji import emojis
from extensions.components import register_action
from utils.ai_prompts import ATTACK_STRATEGIES_PROMPT, CLAN_EXPECTATIONS_PROMPT

# Configuration
RECRUITMENT_STAFF_ROLE = 999140213953671188  # Note: Role ID as integer, not string
LOG_CHANNEL_ID = 1345589195695194113
REMINDER_DELETE_TIMEOUT = 15  # Seconds before auto-deleting reminder messages
REMINDER_TIMEOUT = 30  # Seconds before allowing another reminder to be sent
TIMEZONE_CONFIRMATION_TIMEOUT = 60  # Seconds to wait for Friend Time bot confirmation

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
        "next": "discord_basic_skills"
    },
    "discord_basic_skills": {
        "title": "## 💬 **Discord Basic Skills**",
        "content": (
            "Let's make sure you're comfortable with Discord basics!\n\n"
            "{red_arrow} **React to this message with any emoji**\n"
            "{blank}{white_arrow} This shows you know how to add reactions\n\n"
            "{red_arrow} **Reply mentioning me (the bot)**\n"
            "{blank}{white_arrow} This shows you know how to mention users\n\n"
            "*These skills are essential for clan communication!*"
        ),
        "next": "discord_basic_skills_2",
        "requires_reaction": True,
        "requires_mention": True
    },
    "discord_basic_skills_2": {
        "title": "## 🎯 **Master Discord Communication**",
        "content": (
            "In Kings, we rely heavily on two key Discord skills:\n\n"
            "⚠️ **Mentions** (pings) – call out a member or a role to grab attention.\n"
            "👍 **Reactions** – respond quickly with an emoji to acknowledge messages.\n\n"
            "*These are the fastest ways to keep our clan chat flowing!*\n\n"
            "-# To continue, type **done**"
        ),
        "next": "age_bracket",
        "requires_done": True
    },
    "age_bracket": {
        "title": "## ⏳ **What's Your Age Bracket?**",
        "content": "**What age bracket do you fall into?**\n\n",
        "next": None,  # This will be handled by button clicks
        "is_button_question": True
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


async def create_attack_strategy_components(summary: str, title: str, show_done_button: bool = True,
                                            include_user_ping: bool = False, user_id: Optional[int] = None) -> list:
    """Create components for displaying attack strategies with optional Done button and user ping"""

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

    components_list = []

    # Add user ping if requested
    if include_user_ping and user_id:
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

    components_list.extend([
        Text(content=title),
        Separator(divider=True),
        Text(content=display_content),
        Text(content="\n💡 _Type your strategies in chat and I'll add them automatically!_")
    ])

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
                                              show_done_button: bool = True,
                                              include_user_ping: bool = False, user_id: Optional[int] = None) -> list:
    """Create components for displaying clan expectations with optional Done button and user ping"""

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

    components_list = []

    # Add user ping if requested
    if include_user_ping and user_id:
        components_list.append(Text(content=f"<@{user_id}>"))
        components_list.append(Separator(divider=True))

    components_list.extend([
        Text(content=title),
        Separator(divider=True),
        Text(content=display_content),
        Text(content="\n💡 _Type your preferences in chat and I'll categorize them automatically!_")
    ])

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


async def send_discord_skills_reminder(channel_id: int, user_id: int, bot_id: int, reaction_done: bool,
                                       mention_done: bool):
    """Send a reminder for discord skills and handle auto-deletion"""

    missing = []
    if not reaction_done:
        missing.append("add a reaction to the message above")
    if not mention_done:
        missing.append(f"mention <@{bot_id}> (me) in a message")

    reminder_components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"<a:eyes_look_around:1393971191995302041> **Hey <@{user_id}>!**"),
                Text(content=f"You still need to: {' and '.join(missing)}"),
                Text(content=f"\n*Check the message above for instructions.*"),
                Text(content=f"\n-# This reminder will delete in {REMINDER_DELETE_TIMEOUT} seconds")
            ]
        )
    ]

    try:
        channel = await bot_instance.rest.fetch_channel(channel_id)
        reminder_msg = await channel.send(
            components=reminder_components,
            user_mentions=True
        )
        print(f"[Questionnaire] Reminder sent with ID: {reminder_msg.id}")

        # Update last reminder time in database
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {"step_data.questionnaire.last_reminder_time": datetime.now(timezone.utc)}}
        )

        # Auto-delete reminder after configured timeout
        async def delete_reminder(msg_id):
            await asyncio.sleep(REMINDER_DELETE_TIMEOUT)
            try:
                await bot_instance.rest.delete_message(channel_id, msg_id)
                print(f"[Questionnaire] Deleted discord skills reminder message {msg_id}")
            except Exception as e:
                print(f"[Questionnaire] Error deleting reminder {msg_id}: {e}")

        # Create the task but don't await it - let it run independently
        asyncio.create_task(delete_reminder(reminder_msg.id))

    except Exception as e:
        print(f"[Questionnaire] Error sending reminder: {e}")
        import traceback
        traceback.print_exc()


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

        # Create initial components with empty summary AND user ping
        components = await create_attack_strategy_components(
            "",
            question_data["title"],
            include_user_ping=True,
            user_id=user_id
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

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

        # Create initial components with empty summary but showing examples AND user ping
        components = await create_clan_expectations_components(
            "",
            question_data["title"],
            content,
            include_user_ping=True,
            user_id=user_id
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

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


async def send_discord_skills_question(channel_id: int, user_id: int):
    """Send the Discord basic skills question that requires reaction and mention"""
    try:
        print(f"[Questionnaire] Sending discord skills question to channel {channel_id}")

        # Update state to track this specific step
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": "discord_basic_skills",
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.discord_skills_reaction": False,
                    "step_data.questionnaire.discord_skills_mention": False,
                    "step_data.questionnaire.discord_skills_message_id": None,
                    "step_data.questionnaire.discord_skills_completed": False,
                    "step_data.questionnaire.last_reminder_time": None  # Initialize reminder time tracking
                }
            }
        )

        question_data = QUESTIONNAIRE_QUESTIONS["discord_basic_skills"]
        content = question_data["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

        # Get the bot's ID
        bot_id = bot_instance.get_me().id

        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"<@{user_id}>"),
                    Separator(divider=True),
                    Text(content=question_data["title"]),
                    Text(content=content),
                    Text(content=f"\n*-# Reply and mention me (<@{bot_id}>) to show you can mention users*"),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        print(f"[Questionnaire] Sent discord skills message with ID: {msg.id}")

        # Store message ID for reaction checking
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    f"messages.questionnaire_discord_basic_skills": str(msg.id),
                    "step_data.questionnaire.discord_skills_message_id": str(msg.id)
                }
            }
        )

        # Start monitoring for reaction and mention (pass bot_id)
        monitor_task = asyncio.create_task(monitor_discord_skills(channel_id, user_id, msg.id, bot_id))
        print(f"[Questionnaire] Started monitor task for discord skills")

    except Exception as e:
        print(f"[Questionnaire] Error sending discord skills question: {e}")
        import traceback
        traceback.print_exc()


async def send_age_bracket_question(channel_id: int, user_id: int):
    """Send the age bracket question with buttons"""
    try:
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": "age_bracket",
                    "step_data.questionnaire.awaiting_response": False  # No text response needed
                }
            }
        )

        question = QUESTIONNAIRE_QUESTIONS["age_bracket"]

        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"<@{user_id}>"),
                    Separator(divider=True),
                    Text(content=question["title"]),
                    Separator(divider=True),
                    Text(content=question["content"]),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**16 & Under** *(Family-Friendly Clan)*"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧒16 & Under",
                            custom_id=f"age_questionnaire:16_under_{channel_id}_{user_id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**17 – 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧑17 – 25",
                            custom_id=f"age_questionnaire:17_25_{channel_id}_{user_id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**Over 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧓Over 25",
                            custom_id=f"age_questionnaire:over_25_{channel_id}_{user_id}",
                        ),
                    ),
                    Text(
                        content="*Don't worry, we're not knocking on your door! Just helps us get to know you better. 😄👍*"),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_age_bracket": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent age bracket question to channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending age bracket question: {e}")
        import traceback
        traceback.print_exc()


async def send_timezone_question(channel_id: int, user_id: int):
    """Send the timezone question after age bracket selection"""
    try:
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": "timezone",
                    "step_data.questionnaire.awaiting_response": False,  # Not awaiting text response
                    "step_data.questionnaire.awaiting_timezone_confirmation": True  # Only waiting for confirmation
                }
            }
        )

        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"<@{user_id}>"),
                    Separator(divider=True),
                    Text(content="## 🌐 **Set Your Time Zone**"),
                    Separator(divider=True),
                    Text(content="To help us match you with the right clan and events, let's set your timezone.\n\n"),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right} "
                                    "**Step 1: Find Your Time Zone**"
                                )
                            )
                        ],
                        accessory=LinkButton(
                            url="https://zones.arilyn.cc/",
                            label="Get My Time Zone 🌐",
                        ),
                    ),
                    Text(
                        content=(
                            "**Example format:** `America/New_York`\n\n"
                            "**Steps:**\n"
                            "1. Click the link above to find your timezone\n"
                            "2. Use the command: </set me:924862149292085268>\n"
                            "3. Paste your timezone when Friend Time bot asks\n"
                            "4. Confirm with **yes** when prompted\n\n"
                            "*I'll wait for Friend Time bot to confirm your timezone is set!*"
                        )
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")]),
                    Text(content="-# Kings Alliance Recruitment – Syncing Schedules, Building Teams!")
                ]
            )
        ]

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_timezone": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent timezone question to channel {channel_id}")

        # Start monitoring for Friend Time bot confirmation
        asyncio.create_task(monitor_timezone_completion(channel_id, user_id))

    except Exception as e:
        print(f"[Questionnaire] Error sending timezone question: {e}")
        import traceback
        traceback.print_exc()


async def monitor_timezone_completion(channel_id: int, user_id: int):
    """Monitor for Friend Time bot timezone confirmation with timeout"""
    try:
        print(f"[Questionnaire] Starting timezone monitor for channel {channel_id}")

        # Wait for the configured timeout
        await asyncio.sleep(TIMEZONE_CONFIRMATION_TIMEOUT)

        # Check if we're still waiting
        current_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        if current_state and current_state.get("step_data", {}).get("questionnaire", {}).get(
                "awaiting_timezone_confirmation", False):
            print(
                f"[Questionnaire] Timezone confirmation timeout after {TIMEZONE_CONFIRMATION_TIMEOUT}s - proceeding anyway")

            # Mark as complete and move on
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.awaiting_timezone_confirmation": False,
                        "step_data.questionnaire.timezone": "Not set (timeout)"  # Mark that it timed out
                    }
                }
            )

            await send_questionnaire_question(channel_id, user_id, "leaders_checking_you_out")

    except Exception as e:
        print(f"[Questionnaire] Error in timezone monitor: {e}")
        import traceback
        traceback.print_exc()


async def monitor_discord_skills(channel_id: int, user_id: int, message_id: int, bot_id: int):
    """Monitor for reaction and mention completion - ONLY for checking completion, not sending reminders"""

    print(f"[Questionnaire] Starting discord skills monitor for channel {channel_id}, user {user_id}")

    try:
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            # Get FRESH state from database each time
            ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
            if not ticket_state:
                print(f"[Questionnaire] Monitor: No ticket state found for channel {channel_id}")
                break

            skills_data = ticket_state.get("step_data", {}).get("questionnaire", {})
            reaction_done = skills_data.get("discord_skills_reaction", False)
            mention_done = skills_data.get("discord_skills_mention", False)

            # Check if we've already moved past this question
            current_question = skills_data.get("current_question", "")
            if current_question != "discord_basic_skills":
                print(f"[Questionnaire] Monitor: Question changed to {current_question}, exiting monitor")
                break

            print(f"[Questionnaire] Monitor check: reaction={reaction_done}, mention={mention_done}")

            # If both completed, move to next question
            if reaction_done and mention_done:
                print(f"[Questionnaire] Discord skills completed for user {user_id}")

                # Update the message to show completion
                try:
                    completion_components = [
                        Container(
                            accent_color=GREEN_ACCENT,
                            components=[
                                Text(content=f"<@{user_id}>"),
                                Separator(divider=True),
                                Text(content="## ✅ **Discord Skills Verified!**"),
                                Text(content=(
                                    "Great job! You've successfully:\n"
                                    "• Added a reaction ✓\n"
                                    f"• Mentioned <@{bot_id}> ✓\n\n"
                                    "*Moving to the next question...*"
                                )),
                                Media(items=[MediaItem(media="assets/Green_Footer.png")])
                            ]
                        )
                    ]

                    await bot_instance.rest.edit_message(
                        channel_id,
                        message_id,
                        components=completion_components,
                        user_mentions=True
                    )
                    print(f"[Questionnaire] Updated discord skills completion message")
                except Exception as e:
                    print(f"[Questionnaire] Error updating discord skills message: {e}")
                    import traceback
                    traceback.print_exc()

                # Update state to mark discord skills as complete before moving on
                await mongo_client.ticket_automation_state.update_one(
                    {"_id": str(channel_id)},
                    {
                        "$set": {
                            "step_data.questionnaire.current_question": "transitioning",
                            "step_data.questionnaire.discord_skills_completed": True,
                            "step_data.questionnaire.awaiting_response": False
                        }
                    }
                )

                # Wait a moment then move to next question
                await asyncio.sleep(2)

                print(f"[Questionnaire] Sending next question: discord_basic_skills_2")

                try:
                    await send_questionnaire_question(channel_id, user_id, "discord_basic_skills_2")
                    print(f"[Questionnaire] Successfully sent discord_basic_skills_2")
                except Exception as e:
                    print(f"[Questionnaire] Error sending next question: {e}")
                    import traceback
                    traceback.print_exc()

                print(f"[Questionnaire] Breaking out of monitor loop")
                break  # EXIT THE LOOP

    except Exception as e:
        print(f"[Questionnaire] Monitor error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[Questionnaire] Monitor task ending for channel {channel_id}")


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
        await channel.send(
            components=components,
            user_mentions=True
        )

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

    # Create the same components but without the Done button AND without ping
    final_components = await create_attack_strategy_components(
        current_summary,
        QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
        show_done_button=False,
        include_user_ping=False  # No ping on final version
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

    # Create the same components but without the Done button AND without ping
    final_components = await create_clan_expectations_components(
        current_summary,
        question_data["title"],
        content,
        show_done_button=False,
        include_user_ping=False  # No ping on final version
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


# Handler for age bracket buttons
@register_action("age_questionnaire", no_return=True)
async def handle_age_bracket_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user selects an age bracket"""

    parts = action_id.split("_")
    bracket = f"{parts[0]}_{parts[1]}"  # e.g. "16_under", "17_25", "over_25"
    channel_id = parts[2]
    user_id = parts[3]

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ This button is only for the ticket owner to click.",
            ephemeral=True
        )
        return

    # Define responses for each age bracket
    age_responses = {
        "16_under": {
            "title": "🎉 **16 & Under Registered!**",
            "content": (
                "Got it! You're bringing that youthful energy!\n\n"
                "We'll find you a family-friendly clan that's the perfect fit for you.\n\n"
            ),
            "gif": "https://c.tenor.com/oxxT2JPSQccAAAAC/tenor.gif"
        },
        "17_25": {
            "title": "🎮 **17–25 Confirmed**",
            "content": (
                "Understood! You're in prime gaming years!\n\n"
                "Time to conquer the Clash world! 🏆\n\n"
            ),
            "gif": "https://c.tenor.com/twdtlMLE8UIAAAAC/tenor.gif"
        },
        "over_25": {
            "title": "🏅 **Age Locked In**",
            "content": (
                "Awesome! Experience meets strategy!\n\n"
                "Welcome to the veteran league of Clashers! 💪\n\n"
            ),
            "gif": "https://c.tenor.com/m6o-4dKGdVAAAAAC/tenor.gif"
        }
    }

    response = age_responses.get(bracket)
    if not response:
        await ctx.respond("❌ Invalid age bracket selection.", ephemeral=True)
        return

    # Store the age bracket in MongoDB
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.responses.age_bracket": bracket,
                "step_data.questionnaire.age_bracket": bracket
            }
        }
    )

    # Create response components
    response_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content=response["title"]),
                Text(content=response["content"]),
                Media(items=[MediaItem(media=response["gif"])]),
                Text(content="-# Age bracket registered successfully!")
            ]
        )
    ]

    # The interaction is already deferred by component_handler, so just delete and send new
    await ctx.interaction.delete_initial_response()

    channel = await bot_instance.rest.fetch_channel(int(channel_id))
    await channel.send(
        components=response_components,
        user_mentions=True
    )

    # Wait 10 seconds then send timezone question
    await asyncio.sleep(10)
    await send_timezone_question(int(channel_id), int(user_id))

    print(f"[Questionnaire] User {user_id} selected age bracket: {bracket}")


async def send_questionnaire_question(channel_id: int, user_id: int, question_key: str):
    """Send a specific questionnaire question"""
    try:
        print(f"[Questionnaire] send_questionnaire_question called with question_key: {question_key}")

        # Special handling for attack strategies with AI
        if question_key == "attack_strategies":
            await send_attack_strategies(channel_id, user_id)
            return

        # Special handling for clan expectations with AI
        if question_key == "future_clan_expectations":
            await send_clan_expectations(channel_id, user_id)
            return

        # Special handling for discord_basic_skills
        if question_key == "discord_basic_skills":
            await send_discord_skills_question(channel_id, user_id)
            return

        # Special handling for age_bracket
        if question_key == "age_bracket":
            await send_age_bracket_question(channel_id, user_id)
            return

        question = QUESTIONNAIRE_QUESTIONS.get(question_key)
        if not question:
            print(f"[Questionnaire] Unknown question key: {question_key}")
            return

        print(f"[Questionnaire] Preparing to send question: {question_key}")

        # Special handling for discord_basic_skills_2
        if question_key == "discord_basic_skills_2":
            components_list = [
                Text(content=f"<@{user_id}>"),
                Separator(divider=True),
                Text(content=question["title"]),
                Separator(divider=True),
                Text(content=question["content"].split("-# To continue")[
                                 0].strip() + "\n\n📝 **To continue, type `done` below**")
            ]
        else:
            # Normal formatting for other questions
            content = question["content"].format(
                red_arrow=str(emojis.red_arrow_right),
                white_arrow=str(emojis.white_arrow_right),
                blank=str(emojis.blank)
            )

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

        print(f"[Questionnaire] Updated state for question: {question_key}")

        # Send the message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_{question_key}": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent question {question_key} to channel {channel_id}, message ID: {msg.id}")

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
        await channel.send(
            components=completion_components,
            user_mentions=True
        )

        print(f"[Questionnaire] Sent completion message for user {user_id} in channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending completion message: {e}")
        import traceback
        traceback.print_exc()


@loader.listener(hikari.GuildReactionAddEvent)
async def on_reaction_add(event: hikari.GuildReactionAddEvent):
    """Monitor for reactions on discord skills message"""

    if not mongo_client or not bot_instance:
        return

    if event.user_id == bot_instance.get_me().id:
        return

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if not ticket_state:
        return

    # Check if this is the discord skills message
    skills_msg_id = ticket_state.get("step_data", {}).get("questionnaire", {}).get("discord_skills_message_id")
    if skills_msg_id and str(event.message_id) == skills_msg_id:
        # Verify it's the right user
        expected_user_id = int(ticket_state.get("discord_id", 0) or
                               ticket_state.get("ticket_info", {}).get("user_id", 0) or
                               ticket_state.get("user_id", 0))

        if event.user_id == expected_user_id:
            print(f"[Questionnaire] User {event.user_id} added reaction to discord skills message")

            # Update reaction completed
            update_result = await mongo_client.ticket_automation_state.update_one(
                {"_id": str(event.channel_id)},
                {"$set": {"step_data.questionnaire.discord_skills_reaction": True}}
            )
            print(f"[Questionnaire] Updated reaction status, modified: {update_result.modified_count}")

            # Verify the update
            updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
            reaction_status = updated_state.get("step_data", {}).get("questionnaire", {}).get("discord_skills_reaction",
                                                                                              False)
            print(f"[Questionnaire] Verified reaction status: {reaction_status}")

            print(f"[Questionnaire] User {event.user_id} completed reaction requirement")


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for questionnaire responses in ticket channels"""

    if not mongo_client or not bot_instance:
        return

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if not ticket_state:
        return

    # Check for Friend Time bot timezone confirmation
    if (event.is_bot and
            ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_timezone_confirmation", False)):

        # Log bot messages for debugging
        content_preview = event.content[:100] if event.content else "(no content - possibly embed)"
        print(
            f"[Questionnaire] Bot message in channel {event.channel_id} from {event.author.username}: {content_preview}...")

        # Check if this is a Friend Time bot confirmation message
        is_timezone_confirmation = False
        timezone_match = None

        # Check for the success pattern in content or embeds
        if event.content:
            # Look for success messages from Friend Time bot
            if ("Successfully set your time zone" in event.content or
                    "Your time zone has been set" in event.content or
                    "Time zone updated" in event.content or
                    ("Congratulations!" in event.content and "You've completed user setup!" in event.content)):
                is_timezone_confirmation = True

                # Try to extract timezone from the message
                lines = event.content.split('\n')
                for line in lines:
                    if "/" in line and (
                            "America" in line or "Europe" in line or "Asia" in line or "Africa" in line or "Australia" in line or "Pacific" in line):
                        # This might be a timezone line
                        import re
                        timezone_pattern = r'([A-Za-z_]+\/[A-Za-z_]+(?:\/[A-Za-z_]+)?)'
                        match = re.search(timezone_pattern, line)
                        if match:
                            timezone_match = match.group(1)
                            break

        # Also check embeds
        if event.message.embeds:
            for embed in event.message.embeds:
                if embed.description:
                    if ("Successfully set your time zone" in embed.description or
                            "Your time zone has been set" in embed.description or
                            "Time zone updated" in embed.description or
                            (
                                    "Congratulations!" in embed.description and "You've completed user setup!" in embed.description)):
                        is_timezone_confirmation = True

                        # Look for timezone in embed fields
                        if embed.fields:
                            for field in embed.fields:
                                if "time zone" in field.name.lower() or "timezone" in field.name.lower():
                                    timezone_match = field.value.strip()
                                    break

        if is_timezone_confirmation:
            print(f"[Questionnaire] Detected Friend Time timezone confirmation in channel {event.channel_id}")

            # Store the timezone if found
            update_data = {
                "step_data.questionnaire.timezone_confirmed": True,
                "step_data.questionnaire.awaiting_timezone_confirmation": False
            }

            if timezone_match:
                print(f"[Questionnaire] Extracted timezone: {timezone_match}")
                update_data["step_data.questionnaire.timezone"] = timezone_match
                update_data["step_data.questionnaire.responses.timezone"] = timezone_match
            else:
                print(f"[Questionnaire] Could not extract timezone from confirmation")
                update_data["step_data.questionnaire.timezone"] = "Set (timezone not extracted)"

            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(event.channel_id)},
                {"$set": update_data}
            )

            # Get user ID from ticket state
            user_id = (
                    ticket_state.get("discord_id") or
                    ticket_state.get("ticket_info", {}).get("user_id") or
                    ticket_state.get("user_id")
            )

            if user_id:
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError):
                    pass

            # Send completion message after a brief delay
            await asyncio.sleep(2)
            await send_questionnaire_question(event.channel_id, user_id, "leaders_checking_you_out")

            return

    # Skip other bot messages
    if event.is_bot:
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

        # Update the message with new components - NO PING on updates
        msg_id = ticket_state.get("messages", {}).get("questionnaire_attack_strategies")
        if msg_id:
            try:
                components = await create_attack_strategy_components(
                    new_summary,
                    QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
                    include_user_ping=False  # No ping on updates
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

        # Update the message with new components - NO PING on updates
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
                    content,
                    include_user_ping=False  # No ping on updates
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

    # Special handling for discord_basic_skills_2 "done" requirement
    if (ticket_state.get("step_data", {}).get("questionnaire", {}).get(
            "current_question") == "discord_basic_skills_2" and
            ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_response")):

        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                expected_user_id = None

        if expected_user_id and event.author_id == expected_user_id:
            # Check if user typed "done"
            if event.content.lower().strip() == "done":
                print(f"[Questionnaire] User typed 'done' for discord_basic_skills_2")

                # Update state
                await mongo_client.ticket_automation_state.update_one(
                    {"_id": str(event.channel_id)},
                    {
                        "$set": {
                            "step_data.questionnaire.responses.discord_basic_skills_2": "done",
                            "step_data.questionnaire.awaiting_response": False
                        }
                    }
                )

                # Delete the "done" message
                try:
                    await event.message.delete()
                except:
                    pass

                # Move to next question
                next_question = QUESTIONNAIRE_QUESTIONS["discord_basic_skills_2"]["next"]
                if next_question:
                    await asyncio.sleep(1)
                    await send_questionnaire_question(event.channel_id, expected_user_id, next_question)

                return  # Exit early, don't process as normal response
            else:
                # User typed something else, remind them
                reminder = await event.channel.send(
                    f"<@{event.author_id}> Please type **done** to continue to the next question.",
                    user_mentions=True
                )

                # Delete their message
                try:
                    await event.message.delete()
                except:
                    pass

                # Delete reminder after a few seconds
                async def delete_reminder():
                    await asyncio.sleep(5)
                    try:
                        await reminder.delete()
                    except:
                        pass

                asyncio.create_task(delete_reminder())
                return  # Exit early

    # MOVED UP: Check if this is a discord skills mention BEFORE general handler
    if (ticket_state.get("step_data", {}).get("questionnaire", {}).get("current_question") == "discord_basic_skills" and
            not ticket_state.get("step_data", {}).get("questionnaire", {}).get("discord_skills_mention", False)):

        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        # Convert to int for comparison
        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                print(f"[Questionnaire] Error converting user_id: {expected_user_id}")
                expected_user_id = None

        if expected_user_id and event.author_id == expected_user_id:
            print(f"[Questionnaire] Discord skills message from user {event.author_id}: {event.content}")

            # Get the bot's ID
            bot_id = bot_instance.get_me().id
            print(f"[Questionnaire] Bot ID is {bot_id}")

            # Check if message contains a mention of the bot
            if f"<@{bot_id}>" in event.content or f"<@!{bot_id}>" in event.content:
                print(f"[Questionnaire] Found bot mention in message!")

                # Update mention completed
                update_result = await mongo_client.ticket_automation_state.update_one(
                    {"_id": str(event.channel_id)},
                    {"$set": {"step_data.questionnaire.discord_skills_mention": True}}
                )
                print(f"[Questionnaire] Updated mention status, modified: {update_result.modified_count}")

                # Verify the update
                updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
                mention_status = updated_state.get("step_data", {}).get("questionnaire", {}).get(
                    "discord_skills_mention", False)
                print(f"[Questionnaire] Verified mention status: {mention_status}")

                print(f"[Questionnaire] User {event.author_id} completed mention requirement")

                # Add the eyes emoji reaction to show completion
                try:
                    await event.message.add_reaction("👀")
                    print(f"[Questionnaire] Added eyes reaction to mention message")
                except Exception as e:
                    print(f"[Questionnaire] Error adding reaction: {e}")
            else:
                print(f"[Questionnaire] No bot mention found in message")

                # Check if we should send a reminder
                last_reminder_time = ticket_state.get("step_data", {}).get("questionnaire", {}).get(
                    "last_reminder_time")

                should_send_reminder = False
                if last_reminder_time is None:
                    should_send_reminder = True
                else:
                    # Check if 30 seconds have passed since last reminder
                    time_since_reminder = (datetime.now(timezone.utc) - last_reminder_time).total_seconds()
                    if time_since_reminder >= REMINDER_TIMEOUT:
                        should_send_reminder = True
                        print(f"[Questionnaire] {time_since_reminder}s since last reminder, sending new one")
                    else:
                        print(f"[Questionnaire] Only {time_since_reminder}s since last reminder, waiting")

                if should_send_reminder:
                    # Get current state for reaction check
                    reaction_done = ticket_state.get("step_data", {}).get("questionnaire", {}).get(
                        "discord_skills_reaction", False)

                    # Send reminder for missing requirements
                    await send_discord_skills_reminder(
                        event.channel_id,
                        event.author_id,
                        bot_id,
                        reaction_done,
                        False  # mention_done is False since we're here
                    )

                # React with a different emoji to show we saw it but it's not complete
                try:
                    await event.message.add_reaction("❓")
                    print(f"[Questionnaire] Added incomplete reaction to non-mention message")
                except Exception as e:
                    print(f"[Questionnaire] Error adding reaction: {e}")

            # DO NOT DELETE THE MESSAGE FOR DISCORD SKILLS - We want to show they completed it!
            return

    # Check if we're in questionnaire step and awaiting response for standard questions
    # This is now AFTER the discord skills check
    if (ticket_state.get("automation_state", {}).get("current_step") == "questionnaire" and
            ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_response") and
            ticket_state.get("automation_state", {}).get("status") != "halted"):

        # Skip if this is discord_basic_skills (already handled above)
        current_question = ticket_state["step_data"]["questionnaire"].get("current_question")
        if current_question == "discord_basic_skills":
            print(f"[Questionnaire] Skipping general handler for discord_basic_skills")
            return

        # Also skip if we're in transition
        if current_question == "transitioning":
            print(f"[Questionnaire] Skipping general handler during transition")
            return

        # Verify message is from ticket creator
        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                expected_user_id = None

        if expected_user_id and event.author_id == expected_user_id:
            # Special handling for timezone question - REMOVED since we're not expecting text input anymore

            # Store the response for other questions
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(event.channel_id)},
                {
                    "$set": {
                        f"step_data.questionnaire.responses.{current_question}": event.content,
                        "step_data.questionnaire.awaiting_response": False
                    }
                }
            )

            # For discord_basic_skills_2, age_bracket, timezone - keep messages visible
            # Only delete for other questions
            if current_question not in ["discord_basic_skills_2", "age_bracket", "timezone"]:
                try:
                    await event.message.delete()
                except:
                    pass

            # Move to next question
            next_question = QUESTIONNAIRE_QUESTIONS.get(current_question, {}).get("next")
            if next_question:
                await asyncio.sleep(1)  # Brief pause
                await send_questionnaire_question(event.channel_id, expected_user_id, next_question)

            print(f"[Questionnaire] Recorded response for {current_question} from user {event.author_id}")


# Initialize when bot starts
@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent):
    global mongo_client, bot_instance

    from utils import bot_data
    mongo_client = bot_data.data.get("mongo")
    bot_instance = bot_data.data.get("bot")

    if mongo_client and bot_instance:
        print("Questionnaire automation system with AI initialized")