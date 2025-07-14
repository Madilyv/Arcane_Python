# extensions/events/message/ticket_automation/handlers/discord_skills.py
"""
Handles Discord basic skills verification.
Requires users to react and reply with a mention to prove basic Discord knowledge.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.emoji import emojis
from utils.constants import GOLD_ACCENT, BLUE_ACCENT
from ..core.state_manager import StateManager
from ..components.builders import create_container_component
from ..utils.constants import (
    QUESTIONNAIRE_QUESTIONS,
    REMINDER_DELETE_TIMEOUT,
    REMINDER_TIMEOUT
)

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the handler"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def send_discord_skills_question(channel_id: int, user_id: int) -> None:
    """Send the Discord basic skills verification question"""

    if not mongo_client or not bot_instance:
        print("[DiscordSkills] Error: Not initialized")
        return

    try:
        question_key = "discord_basic_skills"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Format content
        content = question_data["content"].format(
            red_arrow=str(emojis.red_arrow_right),
            white_arrow=str(emojis.white_arrow_right),
            blank=str(emojis.blank)
        )

        # Create components
        template = {
            "title": question_data["title"],
            "content": content,
            "footer": question_data.get("footer", "React to this message and mention the bot to continue!")
        }

        components = create_container_component(
            template,
            accent_color=GOLD_ACCENT,
            user_id=user_id
        )

        # Update state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.discord_skills_completed": False,
                    "step_data.questionnaire.discord_skills_reaction": False,
                    "step_data.questionnaire.discord_skills_mention": False,
                    "step_data.questionnaire.last_reminder_time": None
                }
            }
        )

        # Send message
        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(
            components=components,
            user_mentions=True
        )

        # Store message ID
        await StateManager.store_message_id(
            channel_id,
            "discord_skills_message_id",
            str(msg.id)
        )

        # Add initial reaction for user to copy
        await msg.add_reaction("✅")

        print(f"[DiscordSkills] Sent question to channel {channel_id}")

        # Start monitoring for completion
        asyncio.create_task(monitor_discord_skills_completion(channel_id, user_id))

    except Exception as e:
        print(f"[DiscordSkills] Error sending question: {e}")
        import traceback
        traceback.print_exc()


async def monitor_discord_skills_completion(channel_id: int, user_id: int) -> None:
    """Monitor for completion of Discord skills requirements"""

    check_interval = 2  # seconds
    max_checks = 300  # 10 minutes total
    checks = 0

    while checks < max_checks:
        await asyncio.sleep(check_interval)
        checks += 1

        # Get current state
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            break

        questionnaire_data = ticket_state.get("step_data", {}).get("questionnaire", {})

        # Check if we're still on this question
        if questionnaire_data.get("current_question") != "discord_basic_skills":
            break

        # Check if both requirements are met
        reaction_done = questionnaire_data.get("discord_skills_reaction", False)
        mention_done = questionnaire_data.get("discord_skills_mention", False)

        if reaction_done and mention_done:
            # Both requirements met, mark as complete
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "step_data.questionnaire.discord_skills_completed": True,
                        "step_data.questionnaire.responses.discord_basic_skills": "completed_requirements"
                    }
                }
            )

            # Send completion message
            await send_skills_completion_message(channel_id, user_id)

            # Wait a bit then move to next question
            await asyncio.sleep(3)
            await QuestionFlow.send_next_question(channel_id, user_id, "discord_basic_skills")

            break

        # Check if reminder is needed
        if not (reaction_done and mention_done):
            await check_and_send_reminder(channel_id, user_id, reaction_done, mention_done)


async def send_skills_completion_message(channel_id: int, user_id: int) -> None:
    """Send a message confirming Discord skills completion"""

    if not bot_instance:
        return

    try:
        template = {
            "title": "✅ **Discord Skills Verified!**",
            "content": (
                "Great job! You've successfully demonstrated basic Discord skills.\n\n"
                "You know how to:\n"
                "• React to messages ✅\n"
                "• Mention users properly ✅\n\n"
                "*Let's continue with your application...*"
            ),
            "footer": None
        }

        components = create_container_component(
            template,
            accent_color=BLUE_ACCENT
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        await channel.send(components=components, user_mentions=False)

    except Exception as e:
        print(f"[DiscordSkills] Error sending completion message: {e}")


async def check_and_send_reminder(
        channel_id: int,
        user_id: int,
        reaction_done: bool,
        mention_done: bool
) -> None:
    """Check if a reminder should be sent and send it if needed"""

    if not mongo_client or not bot_instance:
        return

    # Get last reminder time
    ticket_state = await StateManager.get_ticket_state(str(channel_id))
    if not ticket_state:
        return

    last_reminder = ticket_state.get("step_data", {}).get("questionnaire", {}).get("last_reminder_time")

    # Check if enough time has passed since last reminder
    if last_reminder:
        last_reminder_dt = last_reminder
        if (datetime.now(timezone.utc) - last_reminder_dt).total_seconds() < REMINDER_TIMEOUT:
            return

    # Build reminder message
    missing = []
    if not reaction_done:
        missing.append("✅ React to the message above")
    if not mention_done:
        missing.append(f"💬 Reply with {bot_instance.get_me().mention}")

    if not missing:
        return

    try:
        template = {
            "title": "🔔 **Quick Reminder**",
            "content": f"You still need to: {' and '.join(missing)}",
            "footer": f"This reminder will delete in {REMINDER_DELETE_TIMEOUT} seconds"
        }

        reminder_components = create_container_component(
            template,
            accent_color=GOLD_ACCENT,
            user_id=user_id
        )

        channel = await bot_instance.rest.fetch_channel(channel_id)
        reminder_msg = await channel.send(
            components=reminder_components,
            user_mentions=True
        )

        # Update last reminder time
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {"step_data.questionnaire.last_reminder_time": datetime.now(timezone.utc)}}
        )

        # Auto-delete reminder
        async def delete_reminder(msg_id):
            await asyncio.sleep(REMINDER_DELETE_TIMEOUT)
            try:
                await bot_instance.rest.delete_message(channel_id, msg_id)
            except:
                pass

        asyncio.create_task(delete_reminder(reminder_msg.id))

    except Exception as e:
        print(f"[DiscordSkills] Error sending reminder: {e}")


async def handle_reaction_add(event: hikari.GuildReactionAddEvent) -> None:
    """Handle reaction additions for Discord skills verification"""

    if not mongo_client or not bot_instance:
        return

    # Skip bot reactions
    if event.user_id == bot_instance.get_me().id:
        return

    # Get ticket state
    ticket_state = await StateManager.get_ticket_state(str(event.channel_id))
    if not ticket_state:
        return

    # Check if this is the Discord skills message
    skills_msg_id = ticket_state.get("step_data", {}).get("questionnaire", {}).get("discord_skills_message_id")
    if skills_msg_id and str(event.message_id) == skills_msg_id:
        # Verify it's the right user
        expected_user_id = await StateManager.get_user_id(event.channel_id)

        if event.user_id == expected_user_id:
            # Update reaction completed
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(event.channel_id)},
                {"$set": {"step_data.questionnaire.discord_skills_reaction": True}}
            )
            print(f"[DiscordSkills] User {event.user_id} completed reaction requirement")


async def handle_mention_message(channel_id: int, user_id: int, message: hikari.Message) -> None:
    """Handle mention messages for Discord skills verification"""

    if not mongo_client or not bot_instance:
        return

    # Check if bot is mentioned
    bot_user = bot_instance.get_me()
    if bot_user.id not in message.user_mentions_ids:
        return

    # Update mention completed
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {"$set": {"step_data.questionnaire.discord_skills_mention": True}}
    )

    print(f"[DiscordSkills] User {user_id} completed mention requirement")

    # Delete the mention message to keep channel clean
    try:
        await message.delete()
    except:
        pass