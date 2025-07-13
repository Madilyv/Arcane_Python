# extensions/events/message/message_events.py
import hikari
import lightbulb

loader = lightbulb.Loader()


# Test message handler - uses ticket creator's ID from MongoDB
@loader.listener(hikari.GuildMessageCreateEvent)
async def on_test_message(event: hikari.GuildMessageCreateEvent) -> None:
    """Handle test messages - only works for ticket creator"""
    # Import MongoDB client
    from utils import bot_data
    mongo = bot_data.data.get("mongo")

    if not mongo:
        return

    # Get ticket state to check if user is the ticket creator
    ticket_state = await mongo.ticket_automation_state.find_one({"_id": str(event.channel_id)})
    if not ticket_state:
        return

    # Get the ticket creator's user ID
    ticket_user_id = ticket_state.get("discord_id") or ticket_state.get("ticket_info", {}).get("user_id")
    if not ticket_user_id:
        return

    # Convert to int for comparison
    try:
        ticket_user_id = int(ticket_user_id)
    except (ValueError, TypeError):
        return

    # Check if message is from ticket creator
    if event.author_id != ticket_user_id:
        return

    content = (event.content or "").strip()
    if content == "!test":
        await event.app.rest.create_message(
            channel=event.channel_id,
            content=f"Hello <@{event.author_id}>, this is a test response for your ticket!"
        )


@loader.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    """Handle all guild message create events including attack strategy and clan expectations processing"""

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
        from utils.emoji import emojis

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

    # Check if this is a ticket channel collecting clan expectations
    if (ticket_state and
            ticket_state.get("step_data", {}).get("questionnaire", {}).get("collecting_expectations") and
            ticket_state.get("discord_id") == event.author_id):

        print(f"[Questionnaire] Processing clan expectation: {event.content}")

        # Import the functions from ticket_questionnaire
        from extensions.events.message.ticket_questionnaire import (
            process_clan_expectations_with_ai,
            create_clan_expectations_components,
            QUESTIONNAIRE_QUESTIONS
        )
        from utils.emoji import emojis

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("expectations_summary", "")

        # Process with AI
        new_summary = await process_clan_expectations_with_ai(current_summary, event.content)

        # Update database
        await mongo.ticket_automation_state.update_one(
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
                await bot.rest.edit_message(event.channel_id, msg_id, components=components)
                print(f"[Questionnaire] Updated clan expectations display")
            except Exception as e:
                print(f"[Questionnaire] Error updating clan expectations message: {e}")

        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass  # Ignore if we can't delete

        return  # Don't process any other handlers for this message