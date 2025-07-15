"""
Recruit bidding system implementation
Allows bidding on new recruits with time-limited auctions
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import uuid

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
        recruits = await mongo.new_recruits.find({
            "discordUserId": self.discord_user.id,
            "activeBid": {"$ne": True}
        }).to_list(length=None)

        if not recruits:
            await ctx.respond(
                "No available recruits found for this user.",
                ephemeral=True
            )
            return

        # Create dropdown options
        options = []
        for recruit in recruits[:25]:  # Discord limit is 25 options
            th_emoji = get_th_emoji(recruit.get("townHallLevel", 0))

            option_kwargs = {
                "label": recruit.get("playerName", "Unknown"),
                "description": recruit.get("playerTag", "No tag"),
                "value": recruit["_id"]
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
            "thread_id": getattr(ctx.channel, "parent_id", None) or ctx.channel_id
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
    recruit = await mongo.new_recruits.find_one({"_id": recruit_id})
    if not recruit:
        await ctx.respond("Recruit not found.", ephemeral=True)
        return

    if recruit.get("activeBid", False):
        await ctx.respond("Bidding is already active for this recruit.", ephemeral=True)
        return

    # Atomically set activeBid to true
    result = await mongo.new_recruits.find_one_and_update(
        {
            "_id": recruit_id,
            "activeBid": {"$ne": True}  # Matches false, null, or missing
        },
        {"$set": {"activeBid": True}},
        return_document=True
    )

    if not result:
        await ctx.respond("Bidding is already active for this recruit.", ephemeral=True)
        return

    # Create ticket entry
    bid_end_time = datetime.now(timezone.utc) + timedelta(minutes=BIDDING_DURATION)

    ticket_data = {
        "channelId": store_data["channel_id"],
        "threadId": store_data["thread_id"],
        "discordUserId": recruit["discordUserId"],
        "playerName": recruit["playerName"],
        "playerTag": recruit["playerTag"],
        "townHallLevel": recruit.get("townHallLevel", 0),
        "createdAt": datetime.now(timezone.utc),
        "bidEndTime": bid_end_time,
        "recruitId": recruit_id,
        "startedBy": store_data["invoker_id"]
    }

    ticket_result = await mongo.tickets.insert_one(ticket_data)
    ticket_id = ticket_result.inserted_id

    # Store active session
    active_bidding_sessions[recruit_id] = bid_end_time

    # Create the bidding embed
    components = await create_bidding_embed(
        recruit,
        bid_end_time,
        store_data["invoker_id"],
        ticket_id
    )

    # Send the bidding message in the thread
    try:
        message = await bot.rest.create_message(
            channel=store_data["thread_id"],
            components=components
        )

        # Update ticket with message ID
        await mongo.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"messageId": message.id}}
        )

        # Acknowledge the interaction
        await ctx.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            content="✅ Bidding started successfully!",
            components=[]
        )

        # Schedule the bidding end
        task = asyncio.create_task(
            end_bidding_timer(
                bot, mongo, recruit_id, ticket_id,
                store_data["thread_id"], message.id
            )
        )
        bidding_tasks[recruit_id] = task

    except Exception as e:
        print(f"[Bidding] Error creating bidding message: {e}")
        # Rollback on error
        await mongo.new_recruits.update_one(
            {"_id": recruit_id},
            {"$set": {"activeBid": False}}
        )
        await mongo.tickets.delete_one({"_id": ticket_id})
        await ctx.respond("Failed to start bidding. Please try again.", ephemeral=True)


async def create_bidding_embed(
    recruit: Dict,
    bid_end_time: datetime,
    invoker_id: int,
    ticket_id: str
) -> List[Container]:
    """Create the bidding open embed"""

    # Format the end time
    end_time_str = bid_end_time.strftime("%B %d, %Y at %I:%M %p UTC")

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"# Bidding open for {recruit['playerName']}"),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discordUserId']}>\n"
                    f"• **Player Name:** {recruit['playerName']}\n"
                    f"• **Player Tag:** {recruit['playerTag']}\n"
                    f"• **Town Hall Level:** {recruit.get('townHallLevel', 'Unknown')}"
                )),

                Separator(divider=True),

                Text(content=(
                    "Submit your bids for this player account, the highest bid wins automatically.\n\n"
                    "-# Note: If you don't meet the clan's criteria, you will still forfeit your points. "
                    "Please review the player requirements.\n"
                    "-# Note: In the event of a tie, the system will select the winning clan at random."
                )),

                Text(content=f"**⏰ BIDDING ENDS**\n{end_time_str}"),

                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.SUCCESS,
                            label="Place Bid",
                            emoji="🟢",
                            custom_id=f"place_bid:{ticket_id}"
                        ),
                        Button(
                            style=hikari.ButtonStyle.DANGER,
                            label="Remove Bid",
                            emoji="🔴",
                            custom_id=f"remove_bid:{ticket_id}"
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding Started by <@{invoker_id}>")
            ]
        )
    ]

    return components


@register_action("place_bid", no_return=True)
@lightbulb.di.with_di
async def handle_place_bid(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle place bid button click"""
    ticket_id = action_id

    # Get ticket data
    ticket = await mongo.tickets.find_one({"_id": ticket_id})
    if not ticket:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Check if bidding is still active
    if datetime.now(timezone.utc) >= ticket["bidEndTime"]:
        await ctx.respond("Bidding has ended for this recruit.", ephemeral=True)
        return

    # Get user's clans where they have leadership role
    user_clans = []
    all_clans = await mongo.clans.find().to_list(length=None)

    member = ctx.member
    member_roles = [role.id for role in member.get_roles()]

    for clan_data in all_clans:
        clan = Clan(data=clan_data)
        if clan.leader_role_id in member_roles:
            user_clans.append(clan)

    if not user_clans:
        # Log unauthorized attempt
        log_msg = (
            f"❌ {ctx.user.mention} attempted to place a bid but has no clan leadership roles. "
            f"Recruit: {ticket['playerName']} in <#{ticket['threadId']}>"
        )
        await bot.rest.create_message(channel=LOG_CHANNEL_ID, content=log_msg)

        await ctx.respond(
            "You must have a clan leadership role to place bids.",
            ephemeral=True
        )
        return

    # Create clan selection dropdown
    options = []
    for clan in user_clans[:25]:
        option_kwargs = {
            "label": clan.name,
            "value": clan.tag
        }

        # Handle emoji properly
        if clan.emoji and hasattr(clan, 'partial_emoji') and clan.partial_emoji:
            option_kwargs["emoji"] = clan.partial_emoji

        option = SelectOption(**option_kwargs)
        options.append(option)

    # Store session data
    session_id = str(uuid.uuid4())
    await mongo.button_store.insert_one({
        "_id": session_id,
        "ticket_id": ticket_id,
        "user_id": ctx.user.id,
        "action": "place_bid"
    })

    components = [
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="## Select Clan"),
                Text(content="Choose which clan you're bidding for:"),

                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"select_clan_bid:{session_id}",
                            placeholder="Select a clan...",
                            options=options
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Blue_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, ephemeral=True)


@register_action("select_clan_bid", opens_modal=True)
@lightbulb.di.with_di
async def handle_clan_selection_bid(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle clan selection for bidding"""
    session_id = action_id
    clan_tag = ctx.interaction.values[0]

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Update session with clan
    await mongo.button_store.update_one(
        {"_id": session_id},
        {"$set": {"clan_tag": clan_tag}}
    )

    # Get clan points balance
    clan = await mongo.clans.find_one({"tag": clan_tag})
    if not clan:
        await ctx.respond("Clan not found.", ephemeral=True)
        return

    available_points = clan.get("points", 0)

    # Calculate points already in placeholder bids
    existing_bids = await mongo.clan_bidding.find({
        "bids": {
            "$elemMatch": {
                "clan_tag": clan_tag,
                "placed_by": ctx.user.id
            }
        },
        "is_finalized": False
    }).to_list(length=None)

    placeholder_total = sum(
        bid["amount"]
        for auction in existing_bids
        for bid in auction["bids"]
        if bid["clan_tag"] == clan_tag and bid["placed_by"] == ctx.user.id
    )

    remaining_balance = available_points - placeholder_total

    # Create modal for bid amount
    bid_input = ModalActionRow().add_text_input(
        "bid_amount",
        "Bid Amount",
        placeholder=f"Enter amount (0.5 increments, max: {remaining_balance})",
        required=True,
        min_length=1,
        max_length=10
    )

    await ctx.respond_with_modal(
        title=f"Place Bid - {clan['name']}",
        custom_id=f"submit_bid:{session_id}",
        components=[bid_input]
    )


@register_action("submit_bid", no_return=True, is_modal=True)
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
                bid_amount_str = comp.value.strip()
                break

    # Validate bid amount
    try:
        bid_amount = float(bid_amount_str)
    except ValueError:
        await ctx.respond(
            "❌ Invalid bid amount. Please enter a number.",
            ephemeral=True
        )
        return

    # Check if it's a valid increment (0.5)
    if bid_amount % 0.5 != 0:
        await ctx.respond(
            "❌ Bid amount must be in 0.5 point increments.",
            ephemeral=True
        )
        return

    if bid_amount < 0:
        await ctx.respond(
            "❌ Bid amount cannot be negative.",
            ephemeral=True
        )
        return

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Verify points balance again
    clan = await mongo.clans.find_one({"tag": session["clan_tag"]})
    available_points = clan.get("points", 0)

    # Recalculate placeholder bids
    existing_bids = await mongo.clan_bidding.find({
        "bids": {
            "$elemMatch": {
                "clan_tag": session["clan_tag"],
                "placed_by": ctx.user.id
            }
        },
        "is_finalized": False
    }).to_list(length=None)

    placeholder_total = sum(
        bid["amount"]
        for auction in existing_bids
        for bid in auction["bids"]
        if bid["clan_tag"] == session["clan_tag"] and bid["placed_by"] == ctx.user.id
    )

    if bid_amount > (available_points - placeholder_total):
        await ctx.respond(
            f"❌ Insufficient points! Available: {available_points - placeholder_total} points\n"
            f"(Total: {available_points} - Placeholder bids: {placeholder_total})",
            ephemeral=True
        )
        return

    # Get ticket data
    ticket = await mongo.tickets.find_one({"_id": session["ticket_id"]})
    if not ticket:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Create or update bid entry
    bid_entry = {
        "clan_tag": session["clan_tag"],
        "placed_by": ctx.user.id,
        "amount": bid_amount,
        "timestamp": datetime.now(timezone.utc)
    }

    # Update or create auction entry
    await mongo.clan_bidding.update_one(
        {"player_tag": ticket["playerTag"]},
        {
            "$setOnInsert": {
                "player_tag": ticket["playerTag"],
                "is_finalized": False,
                "winner": "",
                "amount": 0
            },
            "$push": {"bids": bid_entry}
        },
        upsert=True
    )

    # Log the bid
    log_msg = (
        f"💰 {ctx.user.mention} placed {bid_amount} bid for "
        f"{ticket['playerName']} in <#{ticket['threadId']}> "
        f"representing {clan['name']}."
    )
    await bot.rest.create_message(channel=LOG_CHANNEL_ID, content=log_msg)

    # Respond to user
    await ctx.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_CREATE,
        content=f"✅ Bid of {bid_amount} points placed successfully for {clan['name']}!",
        flags=hikari.MessageFlag.EPHEMERAL
    )

    # Clean up session
    await mongo.button_store.delete_one({"_id": session_id})


@register_action("remove_bid", no_return=True)
@lightbulb.di.with_di
async def handle_remove_bid(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle remove bid button click"""
    ticket_id = action_id

    # Get ticket data
    ticket = await mongo.tickets.find_one({"_id": ticket_id})
    if not ticket:
        await ctx.respond("Bidding session not found.", ephemeral=True)
        return

    # Get user's clans with bids
    auction = await mongo.clan_bidding.find_one({"player_tag": ticket["playerTag"]})
    if not auction:
        await ctx.respond("No bids found for this recruit.", ephemeral=True)
        return

    # Find user's bids
    user_bids = [
        bid for bid in auction.get("bids", [])
        if bid["placed_by"] == ctx.user.id
    ]

    if not user_bids:
        await ctx.respond("You have no bids to remove.", ephemeral=True)
        return

    # Get clan info for each bid
    options = []
    for bid in user_bids:
        clan = await mongo.clans.find_one({"tag": bid["clan_tag"]})
        if clan:
            clan_obj = Clan(data=clan)
            option_kwargs = {
                "label": f"{clan_obj.name} - {bid['amount']} points",
                "value": f"{bid['clan_tag']}:{bid['amount']}"
            }

            # Handle emoji properly
            if clan_obj.emoji and hasattr(clan_obj, 'partial_emoji') and clan_obj.partial_emoji:
                option_kwargs["emoji"] = clan_obj.partial_emoji

            option = SelectOption(**option_kwargs)
            options.append(option)

    # Store session data
    session_id = str(uuid.uuid4())
    await mongo.button_store.insert_one({
        "_id": session_id,
        "ticket_id": ticket_id,
        "player_tag": ticket["playerTag"],
        "user_id": ctx.user.id,
        "action": "remove_bid"
    })

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content="## Remove Bid"),
                Text(content="Select which bid to remove:"),

                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"select_bid_remove:{session_id}",
                            placeholder="Select a bid...",
                            options=options
                        )
                    ]
                ),

                Media(items=[MediaItem(media="assets/Red_Footer.png")])
            ]
        )
    ]

    await ctx.respond(components=components, ephemeral=True)


@register_action("select_bid_remove", opens_modal=True)
@lightbulb.di.with_di
async def handle_bid_remove_selection(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle bid selection for removal"""
    session_id = action_id
    selected_value = ctx.interaction.values[0]

    clan_tag, amount_str = selected_value.split(":")
    amount = float(amount_str)

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Update session
    await mongo.button_store.update_one(
        {"_id": session_id},
        {"$set": {"clan_tag": clan_tag, "amount": amount}}
    )

    # Create confirmation modal
    confirm_input = ModalActionRow().add_text_input(
        "confirm",
        "Type 'CONFIRM' to remove your bid",
        placeholder="CONFIRM",
        required=True,
        min_length=7,
        max_length=7
    )

    await ctx.respond_with_modal(
        title=f"Remove Bid of {amount} points?",
        custom_id=f"confirm_remove_bid:{session_id}",
        components=[confirm_input]
    )


@register_action("confirm_remove_bid", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def handle_bid_removal_confirmation(
    ctx: lightbulb.components.ModalContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle bid removal confirmation"""
    session_id = action_id

    # Get confirmation text
    confirm_text = ""
    for row in ctx.interaction.components:
        for comp in row:
            if comp.custom_id == "confirm":
                confirm_text = comp.value.strip()
                break

    if confirm_text.upper() != "CONFIRM":
        await ctx.respond(
            "❌ Removal cancelled. You must type 'CONFIRM' exactly.",
            ephemeral=True
        )
        return

    # Get session data
    session = await mongo.button_store.find_one({"_id": session_id})
    if not session:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return

    # Remove the bid
    result = await mongo.clan_bidding.update_one(
        {"player_tag": session["player_tag"]},
        {
            "$pull": {
                "bids": {
                    "clan_tag": session["clan_tag"],
                    "placed_by": session["user_id"],
                    "amount": session["amount"]
                }
            }
        }
    )

    if result.modified_count > 0:
        # Get clan name for log
        clan = await mongo.clans.find_one({"tag": session["clan_tag"]})
        clan_name = clan["name"] if clan else "Unknown Clan"

        # Log the removal
        ticket = await mongo.tickets.find_one({"_id": session["ticket_id"]})
        log_msg = (
            f"🗑️ {ctx.user.mention} removed their {session['amount']} point bid for "
            f"{ticket['playerName']} in <#{ticket['threadId']}> "
            f"representing {clan_name}."
        )
        await bot.rest.create_message(channel=LOG_CHANNEL_ID, content=log_msg)

        await ctx.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            content=f"✅ Bid of {session['amount']} points removed successfully!",
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
    ticket_id: str,
    thread_id: int,
    message_id: int
):
    """Timer to end bidding after duration expires"""
    try:
        # Wait for bidding duration
        await asyncio.sleep(BIDDING_DURATION * 60)

        # Process the bidding results
        await process_bidding_end(bot, mongo, recruit_id, ticket_id, thread_id, message_id)

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
    ticket_id: str,
    thread_id: int,
    message_id: int
):
    """Process the end of bidding"""

    # Get recruit and ticket data
    recruit = await mongo.new_recruits.find_one({"_id": recruit_id})
    ticket = await mongo.tickets.find_one({"_id": ticket_id})

    if not recruit or not ticket:
        print(f"[Bidding] Missing data for recruit {recruit_id}")
        return

    # Get auction data
    auction = await mongo.clan_bidding.find_one({"player_tag": ticket["playerTag"]})

    # Delete the original bidding message
    try:
        await bot.rest.delete_message(thread_id, message_id)
    except:
        pass

    if not auction or not auction.get("bids"):
        # No bids scenario
        await handle_no_bids(bot, mongo, recruit, ticket, thread_id)
    elif len(auction["bids"]) == 1:
        # Single bid scenario
        await handle_single_bid(bot, mongo, recruit, ticket, auction, thread_id)
    else:
        # Multiple bids scenario
        await handle_multiple_bids(bot, mongo, recruit, ticket, auction, thread_id)

    # Mark recruit as no longer in active bidding
    await mongo.new_recruits.update_one(
        {"_id": recruit_id},
        {"$set": {"activeBid": False}}
    )


async def handle_no_bids(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit: Dict,
    ticket: Dict,
    thread_id: int
):
    """Handle scenario where no bids were placed"""

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"# Bids for {recruit['playerName']}"),

                Separator(divider=True),

                Text(content="## No bids were submitted."),

                Text(content=(
                    "<@&1088914884999249940>, please check for interest in this account "
                    "and assign it to the clan with the highest points."
                )),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding ended at {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}")
            ]
        )
    ]

    await bot.rest.create_message(channel=thread_id, components=components)


async def handle_single_bid(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    recruit: Dict,
    ticket: Dict,
    auction: Dict,
    thread_id: int
):
    """Handle scenario where only one bid was placed"""

    bid = auction["bids"][0]
    clan = await mongo.clans.find_one({"tag": bid["clan_tag"]})
    clan_obj = Clan(data=clan) if clan else None

    # Return bid points
    if clan:
        await mongo.clans.update_one(
            {"tag": bid["clan_tag"]},
            {"$inc": {"points": bid["amount"]}}
        )

    components = [
        Container(
            accent_color=GOLD_ACCENT,
            components=[
                Text(content=f"# Bids for {recruit['playerName']}"),

                Text(content="## 🏆 Bid Result: Single Bidder"),

                Text(content=(
                    f"Only one bid was submitted. **{clan_obj.name if clan_obj else 'Unknown Clan'}** "
                    f"has won the account by default.\n\n"
                    "All bid points have been returned automatically due to low interest."
                )),

                Separator(divider=True),

                Text(content="## Candidate Information"),
                Text(content=(
                    f"• **Discord ID:** <@{recruit['discordUserId']}>\n"
                    f"• **Player Name:** {recruit['playerName']}\n"
                    f"• **Player Tag:** {recruit['playerTag']}\n"
                    f"• **Town Hall Level:** {recruit.get('townHallLevel', 'Unknown')}"
                )),

                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                Text(content=f"-# Bidding ended at {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}")
            ]
        )
    ]

    await bot.rest.create_message(channel=thread_id, components=components)

    # Finalize the auction
    await mongo.clan_bidding.update_one(
        {"player_tag": ticket["playerTag"]},
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
    ticket: Dict,
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

    # Create all bids list
    all_bids_text = []
    for i, bid in enumerate(sorted(auction["bids"], key=lambda x: x["amount"], reverse=True), 1):
        clan_data = await mongo.clans.find_one({"tag": bid["clan_tag"]})
        clan_name = clan_data["name"] if clan_data else "Unknown Clan"
        bidder = await bot.rest.fetch_user(bid["placed_by"])
        bidder_name = bidder.username if bidder else "Unknown User"

        bid_text = f"{i}. • **{clan_name}** • _Bid by {bidder_name}_ ⚡ • **{bid['amount']}**"
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
                    f"• **Discord ID:** <@{recruit['discordUserId']}>\n"
                    f"• **Player Name:** {recruit['playerName']}\n"
                    f"• **Player Tag:** {recruit['playerTag']}\n"
                    f"• **Town Hall Level:** {recruit.get('townHallLevel', 'Unknown')}"
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
        {"player_tag": ticket["playerTag"]},
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