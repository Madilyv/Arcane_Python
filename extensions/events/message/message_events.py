# extensions/events/message/message_events.py
import os
import hikari
import lightbulb

loader = lightbulb.Loader()

ALLOWED_USER_ID = 505227988229554179


@loader.listener(hikari.MessageCreateEvent)
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if event.is_bot or event.is_webhook:
        return

    # MINE! NOT YOURS!! MINE!!!
    if event.author_id != ALLOWED_USER_ID:
        return
    content = (event.content or "").strip()
    if content == "!test":
        await event.app.rest.create_message(
            channel=event.channel_id,
            content="Hello, this is a test response!"
        )


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    """Handle all guild message create events including attack strategy processing"""

    # Skip bot messages
    if event.is_bot:
        return

    # Import MongoDB client
    from utils import bot_data
    mongo = bot_data.data.get("mongo")
    bot = bot_data.data.get("bot")

    if not mongo or not bot:
        return

    # Check if this is a ticket channel collecting attack strategies
    ticket_state = await mongo.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if (ticket_state and
            ticket_state.get("step_data", {}).get("questionnaire", {}).get("collecting_strategies") and
            ticket_state.get("discord_id") == event.author_id):

        print(f"[Questionnaire] Processing attack strategy: {event.content}")

        # Import the functions from ticket_questionnaire
        from extensions.events.message.ticket_questionnaire import (
            process_attack_strategies_with_ai,
            create_attack_strategy_components,
            QUESTIONNAIRE_QUESTIONS
        )

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

        # Process with AI
        new_summary = await process_attack_strategies_with_ai(current_summary, event.content)

        # Update database
        await mongo.ticket_automation_state.update_one(
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
                await bot.rest.edit_message(event.channel_id, msg_id, components=components)
                print(f"[Questionnaire] Updated attack strategy display")
            except Exception as e:
                print(f"[Questionnaire] Error updating attack strategy message: {e}")

        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass  # Ignore if we can't delete

        return  # Don't process any other handlers for this message