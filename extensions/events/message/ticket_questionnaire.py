# extensions/events/message/ticket_questionnaire.py
"""
Ticket questionnaire automation system.

Features:
- Interview process selection (Bot-driven vs Speak with Recruiter)
- Attack strategies questionnaire
- Automation halt functionality for manual takeover
- Sequential question flow management
"""

import asyncio
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

# Configuration
RECRUITMENT_STAFF_ROLE = 999140213953671188  # Note: Role ID as integer, not string
LOG_CHANNEL_ID = 1345589195695194113

# Global variables
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
loader = lightbulb.Loader()


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
                                custom_id=f"start_bot_interview:{channel_id}_{user_id}",
                                label="🤖 Start Bot-Driven Interview"
                            ),
                            Button(
                                style=hikari.ButtonStyle.SUCCESS,
                                custom_id=f"speak_with_recruiter:{channel_id}_{user_id}",
                                label="🗣️ Speak with Recruiter"
                            )
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        # Send the message
        message = await bot_instance.rest.create_message(
            channel=channel_id,
            components=components,
            user_mentions=[user_id]
        )

        # Store message ID in MongoDB
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "messages.interview_selection": str(message.id),
                    "step_data.questionnaire.selection_sent": True
                }
            }
        )

        print(f"[Questionnaire] Sent interview selection prompt in channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending interview selection: {e}")


# Handler for "Speak with Recruiter" button
@register_action("speak_with_recruiter", no_return=True)
@lightbulb.di.with_di
async def handle_speak_with_recruiter(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle when user chooses to speak with a recruiter"""

    channel_id, user_id = action_id.split("_")

    # Verify it's the correct user
    if str(ctx.user.id) != user_id:
        await ctx.respond(
            "❌ Only the ticket creator can make this selection.",
            ephemeral=True
        )
        return

    # Update the message to show selection
    selection_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ✅ **Recruiter Interview Selected!**"),
                Text(content=(
                    f"<@&{RECRUITMENT_STAFF_ROLE}>, time to step up and handle this interview! "
                    "He's looking for a real person—not a bot (unless it works harder than you lot). "
                    f"Let's get moving, chop chop! <a:sentient_robot_laugh:1314988181413695498>"
                )),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await ctx.interaction.edit_initial_response(
        components=selection_components,
        user_mentions=[],
        role_mentions=[RECRUITMENT_STAFF_ROLE]
    )

    # Update MongoDB to halt automation
    await mongo.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "automation_state.status": "halted",
                "automation_state.halted_reason": "user_requested_recruiter",
                "step_data.questionnaire.interview_type": "recruiter",
                "step_data.questionnaire.halted_at": datetime.now(timezone.utc)
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "selected_recruiter_interview",
                    "details": {"user_id": user_id}
                }
            }
        }
    )

    print(f"[Questionnaire] User {user_id} selected recruiter interview - automation halted")


# Handler for "Start Bot-Driven Interview" button
@register_action("start_bot_interview", no_return=True)
@lightbulb.di.with_di
async def handle_start_bot_interview(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle when user chooses bot-driven interview"""

    channel_id, user_id = action_id.split("_")

    # Verify it's the correct user
    if str(ctx.user.id) != user_id:
        await ctx.respond(
            "❌ Only the ticket creator can make this selection.",
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
    await mongo.ticket_automation_state.update_one(
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

    # Send first question (attack strategies)
    await send_questionnaire_question(int(channel_id), int(user_id), "attack_strategies")


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
            "{blank}{white_arrow} _e.g. Crystal league or no preference_\n\n"
            "{red_arrow} **Preferred playstyle?**\n"
            "{blank}{white_arrow} Competitive\n"
            "{blank}{white_arrow} Casual\n"
            "{blank}{white_arrow} Zen _Type __What is Zen__ to learn more._\n"
            "{blank}{white_arrow} FWA _Type __What is FWA__ to learn more._"
        ),
        "next": "discord_basic_skills"
    },
    "discord_basic_skills": {
        "title": "## 🎓 **Discord Basics Check**",
        "content": (
            "Hey there! Before we proceed, let's confirm you're comfy with our core Discord features:\n\n"
            "1️⃣ **React** to this message with any emoji of your choice.\n"
            "2️⃣ **Mention** your recruiter in this thread (e.g. <@1386722406051217569>).\n\n"
            "*These steps help us make sure you can react and ping others; key skills for smooth clan comms!*"
        ),
        "has_gif": True,
        "gif_url": "https://c.tenor.com/oEkj7apTtT4AAAAC/tenor.gif",
        "next": "discord_basic_skills_2",
        "requires_reaction": True,
        "requires_mention": True
    },
    "discord_basic_skills_2": {
        "title": "## 🎯 **Master Discord Communication**",
        "content": (
            "In **Kings**, we rely heavily on two key Discord skills:\n\n"
            "🔔 **Mentions** (pings) – call out a member or a role to grab attention.\n"
            "👍 **Reactions** – respond quickly with an emoji to acknowledge messages.\n\n"
            "*These are the fastest ways to keep our clan chat flowing!*"
        ),
        "next": "age_bracket_timezone"
    },
    "age_bracket_timezone": {
        "title": "## 🎂 **Age Bracket & Timezone**",
        "content": (
            "Almost there! Just a couple more quick details:\n\n"
            "{red_arrow} **What's your age bracket?**\n"
            "{blank}{white_arrow} Under 18\n"
            "{blank}{white_arrow} 18-24\n"
            "{blank}{white_arrow} 25-34\n"
            "{blank}{white_arrow} 35+\n\n"
            "{red_arrow} **What's your timezone or UTC offset?**\n"
            "{blank}{white_arrow} _e.g., EST, PST, UTC+8, etc._\n\n"
            "*This helps us match you with clanmates in similar time zones for better coordination!*"
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


async def send_questionnaire_question(channel_id: int, user_id: int, question_key: str):
    """Send a specific questionnaire question"""
    try:
        question = QUESTIONNAIRE_QUESTIONS.get(question_key)
        if not question:
            print(f"[Questionnaire] Unknown question key: {question_key}")
            return

        # Format the content with emoji placeholders
        content = question["content"].format(
            red_arrow=emojis.red_arrow_right,
            white_arrow=emojis.white_arrow_right,
            blank=emojis.blank
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
                Media(items=[MediaItem(media="assets/Red_Footer.png")])
            )

        components = [
            Container(
                accent_color=RED_ACCENT,
                components=components_list
            )
        ]

        # Send the message
        message = await bot_instance.rest.create_message(
            channel=channel_id,
            components=components,
            user_mentions=[user_id]
        )

        # Store message ID and update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    f"messages.questionnaire_{question_key}": str(message.id),
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True
                }
            }
        )

        print(f"[Questionnaire] Sent {question_key} question in channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending {question_key} question: {e}")


async def trigger_questionnaire(channel_id: int, user_id: int):
    """Trigger the questionnaire step for a ticket"""

    # Update ticket state
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "automation_state.current_step": "questionnaire",
                "step_data.questionnaire": {
                    "started": True,
                    "completed": False,
                    "timestamp": datetime.now(timezone.utc),
                    "responses": {}
                }
            }
        }
    )

    # Send the interview selection prompt
    await send_interview_selection_prompt(channel_id, user_id)


# Message listener for questionnaire responses
@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for responses to questionnaire questions"""

    if not mongo_client or not bot_instance:
        return

    # Ignore bot messages
    if event.is_bot:
        return

    channel_id = event.channel_id

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not ticket_state:
        return

    # Check if we're in questionnaire step and awaiting response
    if (ticket_state["automation_state"]["current_step"] != "questionnaire" or
            not ticket_state["step_data"]["questionnaire"].get("awaiting_response") or
            ticket_state["automation_state"]["status"] == "halted"):
        return

    # Verify message is from ticket creator
    if event.author_id != int(ticket_state["ticket_info"]["user_id"]):
        return

    current_question = ticket_state["step_data"]["questionnaire"].get("current_question")


# Message listener for questionnaire responses
@loader.listener(hikari.GuildMessageCreateEvent)
async def on_questionnaire_response(event: hikari.GuildMessageCreateEvent):
    """Listen for responses to questionnaire questions"""

    if not mongo_client or not bot_instance:
        return

    # Ignore bot messages
    if event.is_bot:
        return

    channel_id = event.channel_id

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not ticket_state:
        return

    # Check if we're in questionnaire step and awaiting response
    if (ticket_state["automation_state"]["current_step"] != "questionnaire" or
            not ticket_state["step_data"]["questionnaire"].get("awaiting_response") or
            ticket_state["automation_state"]["status"] == "halted"):
        return

    # Verify message is from ticket creator
    if event.author_id != int(ticket_state["ticket_info"]["user_id"]):
        return

    current_question = ticket_state["step_data"]["questionnaire"].get("current_question")

    # Special handling for discord_basic_skills
    if current_question == "discord_basic_skills":
        # Check if message contains a mention
        if event.message.user_mentions_ids or event.message.role_mention_ids:
            # Mark mention requirement as met
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.discord_skills_mention": True
                    }
                }
            )

            # Check if both requirements are met
            updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
            if updated_state["step_data"]["questionnaire"].get("discord_skills_reaction"):
                # Both requirements met, mark as complete and move to next question
                await mongo_client.ticket_automation_state.update_one(
                    {"_id": str(channel_id)},
                    {
                        "$set": {
                            "step_data.questionnaire.awaiting_response": False,
                            "step_data.questionnaire.responses.discord_basic_skills": "completed_requirements"
                        }
                    }
                )
                await event.message.add_reaction("✅")
                await asyncio.sleep(1)
                await send_questionnaire_question(channel_id, event.author_id, "discord_basic_skills_2")
            else:
                await event.message.add_reaction("👀")
        else:
            # No mention found, just acknowledge
            await event.message.add_reaction("👀")
        return

    # Store the response
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                f"step_data.questionnaire.responses.{current_question}": event.content,
                "step_data.questionnaire.awaiting_response": False
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "questionnaire_response",
                    "details": {
                        "question": current_question,
                        "response": event.content[:100] + "..." if len(event.content) > 100 else event.content
                    }
                }
            }
        }
    )

    # Send confirmation
    await event.message.add_reaction("✅")

    # Get the next question
    question_info = QUESTIONNAIRE_QUESTIONS.get(current_question)
    next_question = question_info.get("next") if question_info else None

    if next_question:
        # Wait a moment before sending next question
        await asyncio.sleep(2)
        await send_questionnaire_question(channel_id, event.author_id, next_question)
    else:
        # Questionnaire complete!
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.completed": True,
                    "automation_state.current_step": "clan_selection"
                },
                "$addToSet": {
                    "automation_state.completed_steps": "questionnaire"
                }
            }
        )

        # Send completion message
        completion_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content="## ✅ **Interview Complete!**"),
                    Text(content=(
                        "Thank you for completing the recruitment questionnaire!\n"
                        "Our team will review your responses and match you with the perfect clan.\n\n"
                        "*You'll hear from us soon!*"
                    )),
                    Media(items=[MediaItem(media="assets/Green_Footer.png")])
                ]
            )
        ]

        await bot_instance.rest.create_message(
            channel=channel_id,
            components=completion_components
        )

        print(f"[Questionnaire] Completed all questions for user {event.author_id}")


# Reaction listener for discord_basic_skills
@loader.listener(hikari.GuildReactionAddEvent)
async def on_reaction_add(event: hikari.GuildReactionAddEvent):
    """Listen for reactions on questionnaire messages"""

    if not mongo_client:
        return

    # Get ticket state
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if not ticket_state:
        return

    # Check if we're on discord_basic_skills question
    if (ticket_state["automation_state"]["current_step"] == "questionnaire" and
            ticket_state["step_data"]["questionnaire"].get("current_question") == "discord_basic_skills" and
            event.user_id == int(ticket_state["ticket_info"]["user_id"])):

        # Check if message has both reaction and mention
        message_id = ticket_state.get("messages", {}).get("questionnaire_discord_basic_skills")
        if message_id and str(event.message_id) == message_id:
            # Mark reaction requirement as met
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(event.channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.discord_skills_reaction": True
                    }
                }
            )

            # Check if both requirements are met
            updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(event.channel_id)})
            if updated_state["step_data"]["questionnaire"].get("discord_skills_mention"):
                # Both requirements met, mark response as complete and move to next question
                await mongo_client.ticket_automation_state.update_one(
                    {"_id": str(event.channel_id)},
                    {
                        "$set": {
                            "step_data.questionnaire.awaiting_response": False,
                            "step_data.questionnaire.responses.discord_basic_skills": "completed_requirements"
                        }
                    }
                )
                await asyncio.sleep(1)
                await send_questionnaire_question(event.channel_id, event.user_id, "discord_basic_skills_2")


# Initialize when bot starts
@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent):
    global mongo_client, bot_instance

    from utils import bot_data
    mongo_client = bot_data.data.get("mongo")
    bot_instance = bot_data.data.get("bot")

    if mongo_client and bot_instance:
        print("Questionnaire automation system initialized")