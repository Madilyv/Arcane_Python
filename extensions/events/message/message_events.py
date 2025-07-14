# extensions/events/message/message_events.py
"""
Main message event handler that routes to appropriate automation handlers.
Updated to use the new modular ticket automation structure.
"""

import hikari
import lightbulb
from utils import bot_data

# Import the new ticket automation modules
from .ticket_automation.core import StateManager
from .ticket_automation.handlers import attack_strategies, clan_expectations, discord_skills
from .ticket_automation.handlers.timezone import FRIEND_TIME_BOT_ID, handle_friend_time_message

loader = lightbulb.Loader()


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    """Handle all guild message create events"""

    # Skip bot messages (except Friend Time bot)
    if event.is_bot and event.author_id != FRIEND_TIME_BOT_ID:
        return

    # Get MongoDB and bot instances
    mongo = bot_data.data.get("mongo")
    bot = bot_data.data.get("bot")

    if not mongo or not bot:
        return

    # Initialize StateManager if needed
    StateManager.initialize(mongo, bot)

    # Get ticket state for this channel
    ticket_state = await StateManager.get_ticket_state(str(event.channel_id))
    if not ticket_state:
        return

    # Check if automation is active
    if not await StateManager.is_automation_active(event.channel_id):
        return

    # Handle Friend Time bot messages
    if event.author_id == FRIEND_TIME_BOT_ID:
        await handle_friend_time_message(event.message)
        return

    # Get expected user ID for this ticket
    expected_user_id = await StateManager.get_user_id(event.channel_id)
    if not expected_user_id or event.author_id != expected_user_id:
        return

    # Get current questionnaire state
    questionnaire_data = ticket_state.get("step_data", {}).get("questionnaire", {})
    current_question = questionnaire_data.get("current_question")

    # Route to appropriate handler based on current state

    # Check if collecting attack strategies
    if questionnaire_data.get("collecting_strategies", False):
        print(f"[MessageEvents] Processing attack strategy: {event.content}")
        await attack_strategies.process_user_input(
            event.channel_id,
            event.author_id,
            event.content
        )
        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass
        return

    # Check if collecting clan expectations
    if questionnaire_data.get("collecting_expectations", False):
        print(f"[MessageEvents] Processing clan expectation: {event.content}")
        await clan_expectations.process_user_input(
            event.channel_id,
            event.author_id,
            event.content
        )
        # Delete the user's message
        try:
            await event.message.delete()
        except:
            pass
        return

    # Check for Discord skills mention requirement
    if (current_question == "discord_basic_skills" and
            not questionnaire_data.get("discord_skills_mention", False)):
        await discord_skills.handle_mention_message(
            event.channel_id,
            event.author_id,
            event.message
        )
        return

    # Handle standard text responses
    if questionnaire_data.get("awaiting_response", False) and current_question:
        print(f"[MessageEvents] Processing response for {current_question}: {event.content}")

        # Special handling for discord_basic_skills_2 "done" requirement
        if current_question == "discord_basic_skills_2" and event.content.lower().strip() == "done":
            # Record the response
            await StateManager.store_response(
                event.channel_id,
                current_question,
                "done"
            )

            # Import QuestionFlow to move to next question
            from .ticket_automation.core import QuestionFlow
            QuestionFlow.initialize(mongo, bot)

            # Move to next question
            await QuestionFlow.send_next_question(
                event.channel_id,
                event.author_id,
                current_question
            )

            # Keep the "done" message visible
            return

        # Handle timezone responses
        elif current_question == "timezone":
            # Store the timezone response
            await StateManager.store_response(
                event.channel_id,
                current_question,
                event.content
            )
            # Don't delete - Friend Time bot needs to see it
            return

        # Handle other text responses
        else:
            # Store the response
            await StateManager.store_response(
                event.channel_id,
                current_question,
                event.content
            )

            # Delete message for clean channel (except special cases)
            if current_question not in ["discord_basic_skills_2", "age_bracket", "timezone"]:
                try:
                    await event.message.delete()
                except:
                    pass

            # Move to next question if applicable
            from .ticket_automation.core import QuestionFlow
            QuestionFlow.initialize(mongo, bot)

            next_question = QuestionFlow.get_next_question(current_question)
            if next_question:
                await QuestionFlow.send_question(
                    event.channel_id,
                    event.author_id,
                    next_question
                )


@loader.listener(hikari.GuildReactionAddEvent)
async def on_reaction_add(event: hikari.GuildReactionAddEvent) -> None:
    """Monitor for reactions on discord skills message"""

    # Get MongoDB and bot instances
    mongo = bot_data.data.get("mongo")
    bot = bot_data.data.get("bot")

    if not mongo or not bot:
        return

    # Skip bot reactions
    if event.user_id == bot.get_me().id:
        return

    # Pass to discord skills handler
    await discord_skills.handle_reaction_add(event)


@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    """Initialize message event handlers when bot starts"""

    mongo = bot_data.data.get("mongo")
    bot = bot_data.data.get("bot")

    if mongo and bot:
        # Initialize all the ticket automation modules
        from .ticket_automation.core import QuestionnaireManager
        await QuestionnaireManager.initialize(mongo, bot)

        print("[MessageEvents] Ticket automation message handlers initialized")