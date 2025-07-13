# extensions/events/message/ticket_account_collection.py

import asyncio
import hikari
import lightbulb
import coc
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow,
    TextInputBuilder as TextInput,
)

from extensions.components import register_action
from utils.constants import RED_ACCENT, GREEN_ACCENT, BLUE_ACCENT
from utils.mongo import MongoClient
from utils.emoji import emojis

# Import the questionnaire trigger
from extensions.events.message.ticket_questionnaire import trigger_questionnaire

# Configuration
ACCOUNT_PROMPT_DELETE_TIMEOUT = 60  # Seconds before account collection prompts auto-delete
ERROR_MESSAGE_DELETE_TIMEOUT = 15  # Seconds before error messages auto-delete

# Global references (will be set by loader)
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
coc_client: Optional[coc.Client] = None

loader = lightbulb.Loader()


async def send_account_collection_prompt(
        channel_id: int,
        user_id: int,
        ticket_info: Dict[str, Any]
) -> Optional[hikari.Message]:
    """Send the account collection prompt message"""

    # Get bot instance from bot_data if not available globally
    global bot_instance
    if not bot_instance:
        from utils import bot_data
        bot_instance = bot_data.data.get("bot")

    if not bot_instance:
        print(f"[Account Collection] ERROR: Bot instance not available!")
        return None

    try:
        user = await bot_instance.rest.fetch_user(user_id)

        # Create unique action IDs for this ticket
        action_id_base = f"{channel_id}_{user_id}"

        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content=f"{user.mention}"),
                    Text(content="## 🤔 **Do You Have Another Account?**"),
                    Separator(divider=True),
                    Text(content=(
                        "If you'd like to apply with another account, let us know!\n\n"
                        "• Click **Yes** if you want to provide the Player Tag of your other account.\n"
                        "• Click **No** to move to the next step."
                    )),
                    Separator(divider=True),
                    Text(content="*Multiple accounts? No problem!*"),
                    ActionRow(
                        components=[
                            Button(
                                style=hikari.ButtonStyle.SUCCESS,
                                custom_id=f"add_account_yes:{action_id_base}",
                                label="Yes, I have another account",
                                emoji="✅"
                            ),
                            Button(
                                style=hikari.ButtonStyle.SECONDARY,
                                custom_id=f"add_account_no:{action_id_base}",
                                label="No, move on",
                                emoji="➡️"
                            )
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        message = await bot_instance.rest.create_message(
            channel=channel_id,
            components=components,
            user_mentions=[user_id]
        )

        # Get mongo client if needed
        global mongo_client
        if not mongo_client:
            from utils import bot_data
            mongo_client = bot_data.data.get("mongo")

        # Store message ID in MongoDB for later reference
        if mongo_client:
            await mongo_client.ticket_automation_state.update_one(
                {"_id": str(channel_id)},
                {
                    "$set": {
                        "messages.account_collection": str(message.id),
                        "automation_state.current_step": "account_collection"
                    }
                }
            )

        print(f"[Account Collection] Sent prompt message in channel {channel_id}")
        return message

    except Exception as e:
        print(f"[Account Collection] ERROR sending prompt: {e}")
        import traceback
        traceback.print_exc()
        return None


# Handler for "Yes, I have another account" button
@register_action("add_account_yes", opens_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_add_account_yes(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle when user wants to add another account"""

    channel_id, user_id = action_id.split("_")

    # Verify it's the correct user
    if str(ctx.user.id) != user_id:
        await ctx.respond(
            content="❌ This button is only for the ticket creator!",
            ephemeral=True
        )
        return

    # Create modal for player tag input
    player_tag_input = ModalActionRow().add_text_input(
        "player_tag",  # custom_id
        "Player Tag",  # label
        placeholder="Enter your player tag (e.g., #ABC123)",
        style=hikari.TextInputStyle.SHORT,
        required=True,
        min_length=3,
        max_length=20
    )

    await ctx.respond_with_modal(
        title="Add Another Account",
        custom_id=f"add_account_modal:{action_id}",
        components=[player_tag_input]
    )


# Handler for modal submission
@register_action("add_account_modal", is_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_account_modal_submit(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle the modal submission with new player tag"""

    channel_id, user_id = action_id.split("_")

    # Get the player tag from modal using the pattern from your project
    def get_modal_value(custom_id: str) -> str:
        for row in ctx.interaction.components:
            for component in row:
                if component.custom_id == custom_id:
                    return component.value
        return ""

    player_tag = get_modal_value("player_tag").strip()

    # Normalize the tag
    if not player_tag.startswith("#"):
        player_tag = f"#{player_tag}"

    # Defer the response as we need to fetch data
    await ctx.interaction.create_initial_response(
        hikari.ResponseType.DEFERRED_MESSAGE_UPDATE
    )

    try:
        # Fetch player data from coc.py
        player = await coc_client.get_player(player_tag)

        # Get existing ticket data
        ticket_state = await mongo.ticket_automation_state.find_one({"_id": str(channel_id)})

        # Create new recruit entry for this additional account
        new_recruit_data = {
            "discord_id": int(user_id),
            "discord_name": ctx.user.username,
            "player_tag": player.tag,
            "player_name": player.name,
            "townhall_level": player.town_hall,
            "current_clan": getattr(player.clan, "name", "No Clan") if player.clan else "No Clan",
            "current_clan_tag": getattr(player.clan, "tag", None) if player.clan else None,
            "channel_id": int(channel_id),
            "thread_id": int(ticket_state["ticket_info"]["thread_id"]),
            "ticket_type": ticket_state["ticket_info"]["ticket_type"],
            "ticket_number": ticket_state["ticket_info"]["ticket_number"],
            "timestamp": datetime.now(timezone.utc),
            "is_additional_account": True,
            "primary_account_tag": ticket_state["ticket_info"].get("user_tag", None)
        }

        # Store in new_recruits collection
        await mongo.new_recruits.insert_one(new_recruit_data)

        # Create account info display
        account_components = [
            Container(
                accent_color=GREEN_ACCENT,
                components=[
                    Text(content="## ✅ **Additional Account Information**"),
                    Separator(divider=True),
                    Text(content=(
                        f"**Player Name:** {player.name}\n"
                        f"**Player Tag:** {player.tag}\n"
                        f"**Town Hall Level:** {player.town_hall}\n"
                        f"**Current Clan:** {getattr(player.clan, 'name', 'No Clan') if player.clan else 'No Clan'}"
                    )),
                    Separator(divider=True),
                    Text(content="*Thank you for providing this information!*"),
                    Media(items=[MediaItem(media="assets/Green_Footer.png")])
                ]
            )
        ]

        # Send account info message
        await bot_instance.rest.create_message(
            channel=int(channel_id),
            components=account_components
        )

        # Delete the original message
        message_id = ticket_state.get("messages", {}).get("account_collection")
        if message_id:
            try:
                await bot_instance.rest.delete_message(int(channel_id), message_id)
            except:
                pass

        # Wait a moment then resend the collection prompt
        await asyncio.sleep(2)
        await send_account_collection_prompt(int(channel_id), int(user_id), ticket_state["ticket_info"])

        # Update interaction history
        await mongo.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$push": {
                    "interaction_history": {
                        "timestamp": datetime.now(timezone.utc),
                        "action": "additional_account_added",
                        "details": {
                            "player_tag": player.tag,
                            "player_name": player.name,
                            "townhall_level": player.town_hall
                        }
                    }
                }
            }
        )

    except coc.NotFound:
        # Invalid player tag
        error_components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content="## ❌ **Invalid Player Tag**"),
                    Text(content=f"Could not find a player with tag: {player_tag}"),
                    Text(content="Please check the tag and try again."),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")])
                ]
            )
        ]

        await ctx.interaction.edit_initial_response(components=error_components)

        # Resend the collection prompt after delay
        await asyncio.sleep(3)
        ticket_state = await mongo.ticket_automation_state.find_one({"_id": str(channel_id)})
        await send_account_collection_prompt(int(channel_id), int(user_id), ticket_state["ticket_info"])

    except Exception as e:
        # General error
        error_components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content="## ❌ **Error**"),
                    Text(content=f"An error occurred: {str(e)}"),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")])
                ]
            )
        ]

        await ctx.interaction.edit_initial_response(components=error_components)


# Handler for "No, move on" button - UPDATED TO TRIGGER QUESTIONNAIRE
@register_action("add_account_no", no_return=True)
@lightbulb.di.with_di
async def handle_add_account_no(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle when user doesn't want to add another account"""

    channel_id, user_id = action_id.split("_")

    # Verify it's the correct user
    if str(ctx.user.id) != user_id:
        await ctx.respond(
            content="❌ This button is only for the ticket creator!",
            ephemeral=True
        )
        return

    print(f"[Account Collection] User clicked 'No, move on' - channel: {channel_id}")

    # Update the message to show completion
    completion_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ✅ **Account Collection Complete**"),
                Text(content="Moving to the interview process..."),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await ctx.interaction.edit_initial_response(components=completion_components)

    # Update ticket state to next step
    await mongo.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "automation_state.current_step": "questionnaire",
                "step_data.account_collection.completed": True
            },
            "$addToSet": {
                "automation_state.completed_steps": "account_collection"
            },
            "$push": {
                "interaction_history": {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "account_collection_skipped",
                    "details": {}
                }
            }
        }
    )

    print(f"[Account Collection] Updated MongoDB state to questionnaire")

    # Wait a moment for smooth transition
    await asyncio.sleep(2)

    try:
        # Trigger the questionnaire step
        print(f"[Account Collection] Triggering questionnaire for channel {channel_id}")
        await trigger_questionnaire(int(channel_id), int(user_id))
        print(f"[Account Collection] Successfully triggered questionnaire")
    except Exception as e:
        print(f"[Account Collection] ERROR triggering questionnaire: {e}")
        import traceback
        traceback.print_exc()


async def trigger_account_collection(channel_id: int, user_id: int, ticket_info: Dict[str, Any]):
    """Trigger the account collection step for a ticket"""

    print(f"[Account Collection] Triggering for channel {channel_id}, user {user_id}")

    # Get mongo client from bot_data if needed
    global mongo_client
    if not mongo_client:
        from utils import bot_data
        mongo_client = bot_data.data.get("mongo")

    if not mongo_client:
        print(f"[Account Collection] ERROR: MongoDB client not available!")
        return

    try:
        # Update ticket state
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "automation_state.current_step": "account_collection",
                    "step_data.account_collection": {
                        "started": True,
                        "completed": False,
                        "timestamp": datetime.now(timezone.utc)
                    }
                }
            }
        )

        # Send the account collection prompt
        result = await send_account_collection_prompt(channel_id, user_id, ticket_info)
        if result:
            print(f"[Account Collection] Successfully triggered for channel {channel_id}")
        else:
            print(f"[Account Collection] Failed to send prompt for channel {channel_id}")

    except Exception as e:
        print(f"[Account Collection] ERROR in trigger: {e}")
        import traceback
        traceback.print_exc()


# Initialize global references when extension loads
@loader.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent):
    global mongo_client, bot_instance, coc_client

    from utils import bot_data
    mongo_client = bot_data.data.get("mongo")
    bot_instance = bot_data.data.get("bot")
    coc_client = bot_data.data.get("coc_client")

    print("[Account Collection] System initialized")