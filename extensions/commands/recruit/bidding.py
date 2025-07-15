"""
Recruit bidding system implementation
Allows bidding on new recruits with time-limited auctions
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import uuid
from bson import ObjectId

import hikari
import lightbulb
from lightbulb.components import MenuContext, ModalContext

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow,
)

from extensions.components import register_action
from extensions.commands.recruit import recruit
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.emoji import emojis
from utils.constants import RED_ACCENT, GREEN_ACCENT, BLUE_ACCENT, GOLD_ACCENT

# Constants
BIDDING_DURATION = 5  # minutes
LOG_CHANNEL_ID = 1381395856317747302  # Channel for bid logs

# Store active bidding sessions with their end times
active_bidding_sessions: Dict[str, datetime] = {}

# Store bidding tasks for cancellation
bidding_tasks: Dict[str, asyncio.Task] = {}


def get_th_emoji(th_level: int) -> Optional[object]:
    """Get the TH emoji for a given level"""
    emoji_attr = f"TH{th_level}"
    if hasattr(emojis, emoji_attr):
        return getattr(emojis, emoji_attr)
    return None


@recruit.register()
class Bidding(
    lightbulb.SlashCommand,
    name="bidding",
    description="Start a bidding process for available recruits"
):
    discord_user = lightbulb.user(
        "discord_user",
        "Select the Discord user whose accounts you want to bid on"
    )

    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)

        # Get available recruits for the selected user
        # Query for documents where activeBid is not true (includes false, null, or missing)
        # Note: Discord IDs are stored as strings in MongoDB
        recruits = await mongo.new_recruits.find({
            "discord_user_id": str(self.discord_user.id),
            "activeBid": {"$ne": True}
        }).to_list(length=None)

        if not recruits:
            await ctx.respond(
                "No available accounts found for this Discord user. "
                "Accounts may already have active bidding or have been recruited.",
                ephemeral=True
            )
            return

        # Create dropdown options
        options = []
        for recruit in recruits[:25]:  # Discord limit is 25 options
            th_emoji = get_th_emoji(recruit.get("player_th_level", 0))

            option_kwargs = {
                "label": recruit.get("player_name", "Unknown"),
                "description": recruit.get("player_tag", "No tag"),
                "value": str(recruit["_id"])  # Convert ObjectId to string
            }

            # Only add emoji if it has partial_emoji attribute
            if th_emoji and hasattr(th_emoji, 'partial_emoji'):
                option_kwargs["emoji"] = th_emoji.partial_emoji

            option = SelectOption(**option_kwargs)
            options.append(option)

        # Store data for the action handler
        action_id = str(uuid.uuid4())

        await mongo.button_store.insert_one({
            "_id": action_id,
            "invoker_id": ctx.user.id,
            "channel_id": ctx.channel_id,
            "thread_id": ctx.channel_id  # The bidding will happen in the same channel/thread
        })

        # Create the selection menu
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content="## Select a Recruit for Bidding"),
                    Text(content="Choose an account to start the bidding process:"),

                    ActionRow(
                        components=[
                            TextSelectMenu(
                                custom_id=f"select_recruit_bidding:{action_id}",
                                placeholder="Select a recruit...",
                                options=options
                            )
                        ]
                    ),

                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        await ctx.respond(components=components, ephemeral=True)


@register_action("select_recruit_bidding", no_return=True)
@lightbulb.di.with_di
async def handle_recruit_selection(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle recruit selection and start bidding"""
    recruit_id = ctx.interaction.values[0]

    # Get button store data
    store_data = await mongo.button_store.find_one({"_id": action_id})
    if not store_data:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Check if bidding already active (race condition protection)
    recruit = await mongo.new_recruits.find_one({"_id": ObjectId(recruit_id)})
    if not recruit:
        await ctx.respond("Recruit not found.", ephemeral=True)
        return

    if recruit.get("activeBid", False):
        await ctx.respond("Bidding is already active for this recruit.", ephemeral=True)
        return

    # Check if there's an existing unfinalized bid
    existing_bid_doc = await mongo.clan_bidding.find_one({
        "player_tag": recruit["player_tag"],
        "is_finalized": False
    })

    if existing_bid_doc:
        # Clean up any empty/invalid bids
        valid_bids = [b for b in existing_bid_doc.get("bids", []) if b.get("clan_tag")]
        if valid_bids:
            await ctx.respond(
                "There's already an active bidding session for this recruit. Please wait for it to complete.",
                ephemeral=True
            )
            return
        else:
            # Clean up the invalid document
            await mongo.clan_bidding.delete_one({"player_tag": recruit["player_tag"]})

    # Atomically set activeBid to true
    result = await mongo.new_recruits.find_one_and_update(
        {
            "_id": ObjectId(recruit_id),
            "activeBid": {"$ne": True}  # Matches false, null, or missing
        },
        {"$set": {"activeBid": True}},
        return_document=True
    )

    if not result:
        await ctx.respond("Bidding is already active for this recruit.", ephemeral=True)
        return

    # Create bidding session entry in button_store
    bid_end_time = datetime.now(timezone.utc) + timedelta(minutes=BIDDING_DURATION)

    bidding_session_id = f"bidding_{recruit_id}_{str(uuid.uuid4())}"
    bidding_session_data = {
        "_id": bidding_session_id,
        "type": "bidding_session",
        "channelId": store_data["channel_id"],
        "threadId": store_data["thread_id"],
        "discordUserId": recruit["discord_user_id"],
        "playerName": recruit["player_name"],
        "playerTag": recruit["player_tag"],
        "townHallLevel": recruit.get("player_th_level", 0),
        "createdAt": datetime.now(timezone.utc),
        "bidEndTime": bid_end_time,
        "recruitId": recruit_id,
        "startedBy": store_data["invoker_id"],
        "messageId": None  # Will be updated after message is sent
    }

    await mongo.button_store.insert_one(bidding_session_data)

    # Store active session
    active_bidding_sessions[recruit_id] = bid_end_time

    # Create the bidding embed
    components = await create_bidding_embed(
        recruit,
        bid_end_time,
        store_data["invoker_id"],
        bidding_session_id
    )

    # Send the bidding message in the thread
    try:
        message = await bot.rest.create_message(
            channel=store_data["thread_id"],
            components=components
        )

        # Update session with message ID
        await mongo.button_store.update_one(
            {"_id": bidding_session_id},
            {"$set": {"messageId": message.id}}
        )

        # Acknowledge the interaction
        await ctx.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            content="✅ Bidding started successfully!",
            components=[]
        )

        # Create clan_bidding document if it doesn't exist
        # Using upsert to avoid duplicate key errors
        await mongo.clan_bidding.update_one(
            {"player_tag": recruit["player_tag"]},
            {
                "$setOnInsert": {
                    "bids": [],
                    "is_finalized": False,
                    "winner": "",
                    "amount": 0
                }
            },
            upsert=True
        )

        # Schedule the bidding end
        task = asyncio.create_task(
            end_bidding_timer(
                bot, mongo, recruit_id, bidding_session_id,
                store_data["thread_id"], message.id
            )
        )
        bidding_tasks[recruit_id] = task

    except Exception as e:
        print(f"[Bidding] Error creating bidding message: {e}")
        # Rollback on error
        await mongo.new_recruits.update_one(
            {"_id": ObjectId(recruit_id)},
            {"$set": {"activeBid": False}}
        )
        await mongo.button_store.delete_one({"_id": bidding_session_id})
        await ctx.respond("Failed to start bidding. Please try again.", ephemeral=True)


async def create_bidding_embed(
    recruit: Dict,
    bid_end_time: datetime,
    invoker_id: int,
    session_id: str
) -> List[Container]:
    """Create the bidding open embed"""

    # Format the end time
    end_time_str = bid_end_time.strftime("%B %d, %Y at %I:%M %p UTC")

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"# Bidding open for {recruit['player_name']}"),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discord_user_id']}>\n"
                    f"• **Player Name:** {recruit['player_name']}\n"
                    f"• **Player Tag:** {recruit['player_tag']}\n"
                    f"• **Town Hall Level:** {recruit.get('player_th_level', 'Unknown')}"
                )),

                Separator(divider=True),

                Text(content=(
                    "Submit your bids for this player account, the highest bid wins automatically.\n\n"
                    "-# Note: If you don't meet the clan's criteria, you will still forfeit your points. "
                    "Please review the player requirements.\n"
                    "-# Note: In the event of a tie, the system will select the winning clan at random."
                )),

                Separator(divider=True),

                ActionRow(
                    components=[
                        Button(
                            custom_id=f"place_bid:{session_id}",
                            style=hikari.ButtonStyle.PRIMARY,
                            label="Place Bid",
                            emoji="💰"
                        ),
                        Button(
                            custom_id=f"remove_bid:{session_id}",
                            style=hikari.ButtonStyle.DANGER,
                            label="Remove Bid",
                            emoji="❌"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Gold_Footer.png")]),
                Text(content=f"-# Bidding ends at {end_time_str} • Started by <@{invoker_id}>")
            ]
        )
    ]

    return components


@register_action("place_bid", opens_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_place_bid(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle placing a bid"""
    session_id = action_id

    # Get bidding session data
    session = await mongo.button_store.find_one({
        "_id": session_id,
        "type": "bidding_session"
    })
    if not session:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Check if bidding is still active
    if session["bidEndTime"] < datetime.now(timezone.utc):
        await ctx.respond("Bidding has ended for this recruit.", ephemeral=True)
        return

    # Get user's clans where they have leader role
    user_roles = ctx.interaction.member.role_ids
    clans = await mongo.clans.find({
        "leader_role_id": {"$in": user_roles}
    }).to_list(length=None)

    if not clans:
        await ctx.respond(
            "You must have a clan leader role to place bids.",
            ephemeral=True
        )
        return

    # Create select menu for clan selection
    options = []
    for clan in clans[:25]:
        clan_obj = Clan(data=clan)
        option_kwargs = {
            "label": clan_obj.name,
            "value": clan_obj.tag
        }
        if clan_obj.emoji and hasattr(clan_obj.emoji, 'partial_emoji'):
            option_kwargs["emoji"] = clan_obj.emoji.partial_emoji

        options.append(SelectOption(**option_kwargs))

    # Store session data
    bid_session_id = str(uuid.uuid4())
    await mongo.button_store.insert_one({
        "_id": bid_session_id,
        "type": "bid_placement",
        "bidding_session_id": session_id,
        "user_id": ctx.user.id,
        "player_tag": session["playerTag"]
    })

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## Select Clan for Bidding"),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"select_clan_bid:{bid_session_id}",
                            placeholder="Choose a clan...",
                            options=options
                        )
                    ]
                )
            ]
        )
    ]

    await ctx.respond(components=components, ephemeral=True)


@register_action("select_clan_bid", opens_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_clan_selection(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle clan selection and show amount modal"""
    session_id = action_id
    selected_clan = ctx.interaction.values[0]

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Get the parent bidding session
    bidding_session = await mongo.button_store.find_one({
        "_id": session["bidding_session_id"],
        "type": "bidding_session"
    })
    if not bidding_session:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Update session with clan selection
    await mongo.button_store.update_one(
        {"_id": session_id},
        {"$set": {"selected_clan": selected_clan}}
    )

    # Create modal for bid amount
    amount_input = ModalActionRow().add_text_input(
        "bid_amount",
        "Bid Amount (in 0.5 increments)",
        placeholder="e.g., 1.5, 2.0, 2.5",
        required=True,
        max_length=10
    )

    await ctx.respond_with_modal(
        title="Enter Bid Amount",
        custom_id=f"submit_bid:{session_id}",
        components=[amount_input]
    )


@register_action("submit_bid", is_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_bid_submission(
    ctx: lightbulb.components.ModalContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle bid amount submission"""
    session_id = action_id

    # Get bid amount from modal
    bid_amount_str = ""
    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "bid_amount":
                bid_amount_str = comp.value
                break

    # Validate bid amount
    try:
        bid_amount = float(bid_amount_str)
        # Check if it's in 0.5 increments
        if bid_amount % 0.5 != 0 or bid_amount < 0:
            raise ValueError("Invalid increment")
    except ValueError:
        await ctx.respond(
            "Invalid bid amount. Please use increments of 0.5 (e.g., 1.0, 1.5, 2.0)",
            ephemeral=True
        )
        return

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Get clan data and check points
    clan = await mongo.clans.find_one({"tag": session["selected_clan"]})
    if not clan:
        await ctx.respond("Clan not found.", ephemeral=True)
        return

    # Calculate available points (total - placeholders)
    available_points = clan.get("points", 0) - clan.get("placeholder_points", 0)
    if bid_amount > available_points:
        await ctx.respond(
            f"Insufficient points. Available: {available_points} points",
            ephemeral=True
        )
        return

    # Check for existing bid
    existing_bid = await mongo.clan_bidding.find_one({
        "player_tag": bidding_session["playerTag"],
        "bids.clan_tag": session["selected_clan"]
    })

    if existing_bid:
        await ctx.respond(
            "Your clan already has a bid on this recruit. Use 'Remove Bid' first.",
            ephemeral=True
        )
        return

    # Place the bid
    await mongo.clan_bidding.update_one(
        {"player_tag": bidding_session["playerTag"]},
        {
            "$push": {
                "bids": {
                    "clan_tag": session["selected_clan"],
                    "placed_by": session["user_id"],
                    "amount": bid_amount,
                    "timestamp": datetime.now(timezone.utc)
                }
            }
        }
    )

    # Update placeholder points
    await mongo.clans.update_one(
        {"tag": session["selected_clan"]},
        {"$inc": {"placeholder_points": bid_amount}}
    )

    # Log the bid
    clan_obj = Clan(data=clan)
    log_msg = (
        f"**New Bid Placed**\n"
        f"Player: `{bidding_session['playerTag']}`\n"
        f"Clan: {clan_obj.name}\n"
        f"Amount: {bid_amount} points\n"
        f"Placed by: <@{session['user_id']}>"
    )
    await bot.rest.create_message(channel=LOG_CHANNEL_ID, content=log_msg)

    await ctx.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_CREATE,
        content=f"✅ Bid of {bid_amount} points placed successfully!",
        flags=hikari.MessageFlag.EPHEMERAL
    )

    # Clean up session
    await mongo.button_store.delete_one({"_id": session_id})


@register_action("remove_bid", opens_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_remove_bid(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle removing a bid"""
    session_id = action_id

    # Get bidding session data
    session = await mongo.button_store.find_one({
        "_id": session_id,
        "type": "bidding_session"
    })
    if not session:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Get user's clans
    user_roles = ctx.interaction.member.role_ids
    clans = await mongo.clans.find({
        "leader_role_id": {"$in": user_roles}
    }).to_list(length=None)

    if not clans:
        await ctx.respond("No clans found with your leader role.", ephemeral=True)
        return

    # Get bids for this player
    bid_doc = await mongo.clan_bidding.find_one({"player_tag": session["playerTag"]})
    if not bid_doc or not bid_doc.get("bids"):
        await ctx.respond("No bids found.", ephemeral=True)
        return

    # Filter bids to only show user's clans
    clan_tags = [c["tag"] for c in clans]
    user_bids = [b for b in bid_doc["bids"] if b["clan_tag"] in clan_tags]

    if not user_bids:
        await ctx.respond("You have no active bids to remove.", ephemeral=True)
        return

    # Create options for bid selection
    options = []
    for bid in user_bids:
        clan_data = next((c for c in clans if c["tag"] == bid["clan_tag"]), None)
        if clan_data:
            clan_obj = Clan(data=clan_data)
            option_kwargs = {
                "label": f"{clan_obj.name} - {bid['amount']} points",
                "value": bid["clan_tag"]
            }
            if clan_obj.emoji and hasattr(clan_obj.emoji, 'partial_emoji'):
                option_kwargs["emoji"] = clan_obj.emoji.partial_emoji
            options.append(SelectOption(**option_kwargs))

    # Store session
    remove_session_id = str(uuid.uuid4())
    await mongo.button_store.insert_one({
        "_id": remove_session_id,
        "type": "bid_removal",
        "bidding_session_id": session_id,
        "user_id": ctx.user.id,
        "player_tag": session["playerTag"]
    })

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content="## Select Bid to Remove"),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"confirm_remove_bid:{remove_session_id}",
                            placeholder="Choose a bid to remove...",
                            options=options
                        )
                    ]
                )
            ]
        )
    ]

    await ctx.respond(components=components, ephemeral=True)


@register_action("confirm_remove_bid", opens_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_remove_confirmation(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Show confirmation modal for bid removal"""
    session_id = action_id
    clan_tag = ctx.interaction.values[0]

    # Update session
    await mongo.button_store.update_one(
        {"_id": session_id},
        {"$set": {"clan_to_remove": clan_tag}}
    )

    # Get bid details
    session = await mongo.button_store.find_one({"_id": session_id})
    bid_doc = await mongo.clan_bidding.find_one({"player_tag": session["player_tag"]})
    bid = next((b for b in bid_doc["bids"] if b["clan_tag"] == clan_tag), None)

    if not bid:
        await ctx.respond("Bid not found.", ephemeral=True)
        return

    # Create confirmation modal
    confirm_input = ModalActionRow().add_text_input(
        "confirm",
        f"Type 'REMOVE' to confirm removal of {bid['amount']} point bid",
        placeholder="REMOVE",
        required=True,
        max_length=6
    )

    await ctx.respond_with_modal(
        title="Confirm Bid Removal",
        custom_id=f"execute_remove_bid:{session_id}",
        components=[confirm_input]
    )


@register_action("execute_remove_bid", is_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_bid_removal(
    ctx: lightbulb.components.ModalContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Execute the bid removal"""
    session_id = action_id

    # Check confirmation
    confirm_text = ""
    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "confirm":
                confirm_text = comp.value
                break

    if confirm_text != "REMOVE":
        await ctx.respond("Removal cancelled. You must type 'REMOVE' exactly.", ephemeral=True)
        return

    # Get session
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired.", ephemeral=True)
        return

    # Get the parent bidding session for player tag
    bidding_session = await mongo.button_store.find_one({
        "_id": session["bidding_session_id"],
        "type": "bidding_session"
    })

    # Get bid details for logging
    bid_doc = await mongo.clan_bidding.find_one({"player_tag": bidding_session["playerTag"] if bidding_session else session["player_tag"]})
    bid = next((b for b in bid_doc["bids"] if b["clan_tag"] == session["clan_to_remove"]), None)

    if bid:
        # Remove the bid
        player_tag = bidding_session["playerTag"] if bidding_session else session["player_tag"]
        await mongo.clan_bidding.update_one(
            {"player_tag": player_tag},
            {"$pull": {"bids": {"clan_tag": session["clan_to_remove"]}}}
        )

        # Restore placeholder points
        await mongo.clans.update_one(
            {"tag": session["clan_to_remove"]},
            {"$inc": {"placeholder_points": -bid["amount"]}}
        )

        # Get clan name for logging
        clan_data = await mongo.clans.find_one({"tag": session["clan_to_remove"]})
        clan_name = clan_data["name"] if clan_data else "Unknown Clan"

        # Log the removal
        log_msg = (
            f"**Bid Removed**\n"
            f"Player: `{player_tag}`\n"
            f"Clan: {clan_name}\n"
            f"Amount: {bid['amount']} points\n"
            f"Removed by: <@{session['user_id']}>"
        )
        await bot.rest.create_message(channel=LOG_CHANNEL_ID, content=log_msg)

        await ctx.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            content=f"✅ Bid of {bid['amount']} points removed successfully!",
            flags=hikari.MessageFlag.EPHEMERAL
        )
    else:
        await ctx.respond(
            "❌ Bid not found. It may have already been removed.",
            ephemeral=True
        )

    # Clean up session
    await mongo.button_store.delete_one({"_id": session_id})


async def end_bidding_timer(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit_id: str,
    session_id: str,
    thread_id: int,
    message_id: int
):
    """Timer to end bidding after duration expires"""
    try:
        # Wait for bidding duration
        await asyncio.sleep(BIDDING_DURATION * 60)

        # Process the bidding results
        await process_bidding_end(bot, mongo, recruit_id, session_id, thread_id, message_id)

    except asyncio.CancelledError:
        print(f"[Bidding] Timer cancelled for recruit {recruit_id}")
    except Exception as e:
        print(f"[Bidding] Error in timer for recruit {recruit_id}: {e}")
    finally:
        # Clean up
        if recruit_id in active_bidding_sessions:
            del active_bidding_sessions[recruit_id]
        if recruit_id in bidding_tasks:
            del bidding_tasks[recruit_id]


async def process_bidding_end(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit_id: str,
    session_id: str,
    thread_id: int,
    message_id: int
):
    """Process the end of bidding"""

    # Get recruit and session data
    recruit = await mongo.new_recruits.find_one({"_id": ObjectId(recruit_id)})
    session = await mongo.button_store.find_one({
        "_id": session_id,
        "type": "bidding_session"
    })

    if not recruit or not session:
        print(f"[Bidding] Missing data for recruit {recruit_id}")
        return

    # Get auction data
    auction = await mongo.clan_bidding.find_one({"player_tag": session["playerTag"]})

    # Delete the original bidding message
    try:
        await bot.rest.delete_message(thread_id, message_id)
    except:
        pass

    if not auction or not auction.get("bids"):
        # No bids scenario
        await handle_no_bids(bot, mongo, recruit, session, thread_id)
    elif len(auction["bids"]) == 1:
        # Single bid scenario
        await handle_single_bid(bot, mongo, recruit, session, auction, thread_id)
    else:
        # Multiple bids scenario
        await handle_multiple_bids(bot, mongo, recruit, session, auction, thread_id)

    # Mark recruit as no longer in active bidding
    await mongo.new_recruits.update_one(
        {"_id": ObjectId(recruit_id)},
        {"$set": {"activeBid": False}}
    )

    # Clean up bidding session data
    await mongo.button_store.delete_one({"_id": session_id})


async def handle_no_bids(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit: Dict,
    session: Dict,
    thread_id: int
):
    """Handle scenario where no bids were placed"""

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"# Bids for {recruit['player_name']}"),

                Separator(divider=True),

                Text(content="## No bids were submitted."),
                Text(content=(
                    "@here Leadership, I need help with finding a suitable clan for this recruit.\n\n"
                    f"<@&1086035176166977617>, please find a suitable clan for <@{recruit['discord_user_id']}>."
                )),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discord_user_id']}>\n"
                    f"• **Player Name:** {recruit['player_name']}\n"
                    f"• **Player Tag:** {recruit['player_tag']}\n"
                    f"• **Town Hall Level:** {recruit.get('player_th_level', 'Unknown')}"
                )),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding ended at {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}")
            ]
        )
    ]

    # Send with role pings
    await bot.rest.create_message(
        channel=thread_id,
        content="<@&1086035176166977617>",  # Recruit Lead role
        components=components,
        role_mentions=[1086035176166977617]
    )

    # Finalize the auction with no winner
    await mongo.clan_bidding.update_one(
        {"player_tag": session["playerTag"]},
        {
            "$set": {
                "is_finalized": True,
                "winner": "NO_BIDS",
                "amount": 0
            }
        }
    )


async def handle_single_bid(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit: Dict,
    session: Dict,
    auction: Dict,
    thread_id: int
):
    """Handle scenario where only one bid was placed"""

    bid = auction["bids"][0]
    clan = await mongo.clans.find_one({"tag": bid["clan_tag"]})
    clan_obj = Clan(data=clan) if clan else None

    # Refund the placeholder points (no charge for single bid)
    await mongo.clans.update_one(
        {"tag": bid["clan_tag"]},
        {"$inc": {"placeholder_points": -bid["amount"]}}
    )

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=f"## Winning Bid: {clan_obj.name if clan_obj else 'Unknown'} – FREE"),

                Text(content=(
                    f"**{clan_obj.name if clan_obj else 'Unknown Clan'}** "
                    f"has won the account by default.\n\n"
                    "All bid points have been returned automatically due to low interest."
                )),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discord_user_id']}>\n"
                    f"• **Player Name:** {recruit['player_name']}\n"
                    f"• **Player Tag:** {recruit['player_tag']}\n"
                    f"• **Town Hall Level:** {recruit.get('player_th_level', 'Unknown')}"
                )),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding ended at {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}")
            ]
        )
    ]

    await bot.rest.create_message(channel=thread_id, components=components)

    # Finalize the auction
    await mongo.clan_bidding.update_one(
        {"player_tag": session["playerTag"]},
        {
            "$set": {
                "is_finalized": True,
                "winner": bid["clan_tag"],
                "amount": 0  # No points deducted due to single bid
            }
        }
    )


async def handle_multiple_bids(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit: Dict,
    session: Dict,
    auction: Dict,
    thread_id: int
):
    """Handle scenario where multiple bids were placed"""

    # Find highest bid amount
    highest_amount = max(bid["amount"] for bid in auction["bids"])

    # Find all bids with the highest amount
    top_bids = [bid for bid in auction["bids"] if bid["amount"] == highest_amount]

    # Determine winner
    if len(top_bids) == 1:
        winning_bid = top_bids[0]
        is_tie = False
    else:
        # Random selection for tie
        winning_bid = random.choice(top_bids)
        is_tie = True

    # Get winning clan info
    winning_clan = await mongo.clans.find_one({"tag": winning_bid["clan_tag"]})
    winning_clan_obj = Clan(data=winning_clan) if winning_clan else None

    # Deduct points from winning clan
    if winning_clan:
        await mongo.clans.update_one(
            {"tag": winning_bid["clan_tag"]},
            {"$inc": {"points": -winning_bid["amount"]}}
        )

    # Refund placeholder points for all clans
    for bid in auction["bids"]:
        await mongo.clans.update_one(
            {"tag": bid["clan_tag"]},
            {"$inc": {"placeholder_points": -bid["amount"]}}
        )

    # Create all bids list
    all_bids_text = []
    for i, bid in enumerate(sorted(auction["bids"], key=lambda x: x["amount"], reverse=True), 1):
        clan_data = await mongo.clans.find_one({"tag": bid["clan_tag"]})
        clan_name = clan_data["name"] if clan_data else "Unknown Clan"
        bidder = await bot.rest.fetch_user(bid["placed_by"])
        bidder_name = bidder.username if bidder else "Unknown User"

        bid_text = f"{i}. **{clan_name}** • _Bid by {bidder_name}_ ⚡ • **{bid['amount']}**"
        all_bids_text.append(bid_text)

    # Build the message
    title = f"## Winning Bid: {winning_clan_obj.name if winning_clan_obj else 'Unknown'} – {winning_bid['amount']}"
    if is_tie:
        title += "\n-# Tie-breaker: randomly selected"

    components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content=title),

                Text(content=(
                    f"Congratulations <@&{winning_clan['leader_role_id'] if winning_clan else 0}> Leadership! "
                    f"You've won the bid for this recruit, come claim your new player now!"
                )),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discord_user_id']}>\n"
                    f"• **Player Name:** {recruit['player_name']}\n"
                    f"• **Player Tag:** {recruit['player_tag']}\n"
                    f"• **Town Hall Level:** {recruit.get('player_th_level', 'Unknown')}"
                )),

                Separator(divider=True),

                Text(content="## All Bids"),
                Text(content="\n".join(all_bids_text)),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding ended at {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}")
            ]
        )
    ]

    # Send message with role ping
    content = f"<@&{winning_clan['leader_role_id']}>" if winning_clan else None
    await bot.rest.create_message(
        channel=thread_id,
        content=content,
        components=components,
        role_mentions=[winning_clan['leader_role_id']] if winning_clan else []
    )

    # Finalize the auction
    await mongo.clan_bidding.update_one(
        {"player_tag": session["playerTag"]},
        {
            "$set": {
                "is_finalized": True,
                "winner": winning_bid["clan_tag"],
                "amount": winning_bid["amount"]
            }
        }
    )


# Cleanup on module unload
def cleanup_tasks():
    """Cancel all active bidding tasks"""
    for task in bidding_tasks.values():
        if not task.done():
            task.cancel()
    bidding_tasks.clear()
    active_bidding_sessions.clear()


# Create the loader
loader = lightbulb.Loader()
loader.command(recruit)