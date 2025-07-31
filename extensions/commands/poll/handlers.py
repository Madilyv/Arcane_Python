# extensions/commands/poll/handlers.py
"""
Button handlers for poll voting and management.
"""

import hikari
import lightbulb
from datetime import datetime, timezone
from typing import Dict, List

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT, GREEN_ACCENT, GOLD_ACCENT
from extensions.components import register_action
from . import scheduler

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    InteractiveButtonBuilder as Button,
    MessageActionRowBuilder as ActionRow,
    SectionComponentBuilder as Section,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

def create_progress_bar(percentage: float, length: int = 20) -> str:
    """Create a visual progress bar with gradient effect"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    
    # Create gradient effect based on percentage
    if percentage >= 75:
        bar_char = "█"  # Full block for high percentages
    elif percentage >= 50:
        bar_char = "▓"  # Dark shade
    elif percentage >= 25:
        bar_char = "▒"  # Medium shade
    else:
        bar_char = "░"  # Light shade for low percentages
    
    # Build the bar with gradient
    if filled > 0:
        # Add gradient effect at the end
        if filled > 1:
            bar = "█" * (filled - 1) + bar_char
        else:
            bar = bar_char
    else:
        bar = ""
    
    return bar + "░" * empty

def calculate_percentages(votes: Dict[str, int], options: List[dict]) -> Dict[int, tuple]:
    """Calculate vote counts and percentages for each option"""
    # Count votes for each option
    vote_counts = {opt["id"]: 0 for opt in options}
    for user_id, option_id in votes.items():
        if option_id in vote_counts:
            vote_counts[option_id] += 1
    
    total_votes = sum(vote_counts.values())
    
    # Calculate percentages
    results = {}
    for option_id, count in vote_counts.items():
        if total_votes > 0:
            percentage = (count / total_votes) * 100
        else:
            percentage = 0
        results[option_id] = (count, percentage)
    
    return results

async def update_poll_message(
    bot: hikari.GatewayBot,
    mongo: MongoClient,
    poll_data: dict
) -> None:
    """Update the poll message with new vote counts"""
    try:
        # Calculate results
        results = calculate_percentages(poll_data["votes"], poll_data["options"])
        total_votes = len(poll_data["votes"])
        
        # Get emojis from poll data
        emojis = ["🥇", "🥈", "🥉"]
        # All vote buttons are secondary style for cleaner look
        colors = [hikari.ButtonStyle.SECONDARY, hikari.ButtonStyle.SECONDARY, 
                  hikari.ButtonStyle.SECONDARY]
        
        # Rebuild components
        poll_components = []
        
        # Header section with role ping if applicable
        header_components = []
        
        # Add role ping at the top if specified
        if poll_data.get('ping_role_id'):
            header_components.append(Text(content=f"📢 <@&{poll_data['ping_role_id']}> **Active poll!**"))
            header_components.append(Separator(divider=True))
        
        # Ensure ends_at is timezone-aware
        ends_at = poll_data['ends_at']
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        
        header_components.extend([
            Text(content=f"## 📊 {poll_data.get('title', 'Poll')}"),
            Text(content=f"*{poll_data['description']}*"),
            Separator(divider=False),
            Text(content=(
                f"👤 **Created by:** <@{poll_data['creator_id']}> • "
                f"⏰ **Ends:** <t:{int(ends_at.timestamp())}:R>"
            )),
            Separator(divider=True)
        ])
        
        # Update each option with live data
        for i, option in enumerate(poll_data["options"]):
            count, percentage = results[option["id"]]
            progress_bar = create_progress_bar(percentage)
            
            # Get recent voters (last 3)
            recent_voters = []
            for user_id, vote_id in list(poll_data["votes"].items())[-10:]:
                if vote_id == option["id"] and len(recent_voters) < 3:
                    recent_voters.append(f"<@{user_id}>")
            
            voter_text = "👤 " + " ".join(recent_voters) if recent_voters else "*No votes yet*"
            if count > 3:
                voter_text += f" *+{count - 3} more*"
            
            poll_components.append(Text(content=f"{option['emoji']} **{option['text']}**"))
            poll_components.append(Text(content=f"`[{progress_bar}]` **{percentage:.0f}%** ({count} vote{'s' if count != 1 else ''})"))
            poll_components.append(Text(content=voter_text))
            poll_components.append(Separator(divider=False))
        
        poll_components.append(Separator(divider=True))
        
        # Add stats footer before image
        poll_components.append(
            Text(content=f"**Total votes:** {total_votes} • **Status:** 🟢 Live")
        )
        
        # Add footer image
        poll_components.append(
            Media(items=[MediaItem(media="assets/Gold_Footer.png")])
        )
        
        # Create control buttons row FIRST
        control_row = ActionRow()
        control_row.add_component(
            Button(
                style=hikari.ButtonStyle.DANGER,
                label="End Poll",
                custom_id=f"poll_end:{poll_data['_id']}",
                emoji="🛑"
            )
        )
        control_row.add_component(
            Button(
                style=hikari.ButtonStyle.SECONDARY,
                label="View Details",
                custom_id=f"poll_details:{poll_data['_id']}",
                emoji="📊"
            )
        )
        poll_components.append(control_row)
        
        # Create vote buttons SECOND
        vote_buttons = []
        for i, option in enumerate(poll_data["options"]):
            vote_buttons.append(
                Button(
                    style=colors[i] if i < len(colors) else hikari.ButtonStyle.SECONDARY,
                    emoji=option['emoji'],
                    custom_id=f"poll_vote:{poll_data['_id']}:{option['id']}"
                )
            )
        
        # Create vote button row
        vote_row = ActionRow()
        for button in vote_buttons:
            vote_row.add_component(button)
        poll_components.append(vote_row)
        
        # Create the Container
        container = Container(
            accent_color=GOLD_ACCENT,
            components=header_components + poll_components
        )
        
        # Update message
        await bot.rest.edit_message(
            channel=int(poll_data["channel_id"]),
            message=int(poll_data["message_id"]),
            components=[container]
        )
        
    except Exception as e:
        print(f"[Poll] Failed to update poll message: {e}")

@register_action("poll_vote", no_return=True)
@lightbulb.di.with_di
async def handle_poll_vote(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
) -> None:
    """Handle poll vote button clicks"""
    
    # Parse action ID: poll_vote:poll_id:option_id
    parts = action_id.split(":")
    if len(parts) != 2:
        await ctx.respond("❌ Invalid poll data", ephemeral=True)
        return
    
    poll_id, option_id = parts[0], int(parts[1])
    user_id = str(ctx.interaction.user.id)
    
    # Get poll data
    poll_data = await mongo.discord_polls.find_one({"_id": poll_id})
    
    if not poll_data:
        await ctx.respond("❌ Poll not found", ephemeral=True)
        return
    
    if not poll_data["active"]:
        await ctx.respond("❌ This poll has ended", ephemeral=True)
        return
    
    # Check if option exists
    valid_options = [opt["id"] for opt in poll_data["options"]]
    if option_id not in valid_options:
        await ctx.respond("❌ Invalid option", ephemeral=True)
        return
    
    # Get previous vote
    previous_vote = poll_data["votes"].get(user_id)
    
    # Update vote
    poll_data["votes"][user_id] = option_id
    
    # Save to database
    await mongo.discord_polls.update_one(
        {"_id": poll_id},
        {"$set": {f"votes.{user_id}": option_id}}
    )
    
    # Update the poll message
    await update_poll_message(bot, mongo, poll_data)
    
    # Respond to user
    option = next(opt for opt in poll_data["options"] if opt["id"] == option_id)
    if previous_vote and previous_vote != option_id:
        prev_option = next(opt for opt in poll_data["options"] if opt["id"] == previous_vote)
        await ctx.respond(
            f"✅ Vote changed from **{prev_option['text']}** to **{option['text']}**",
            ephemeral=True
        )
    else:
        await ctx.respond(
            f"✅ You voted for **{option['text']}**",
            ephemeral=True
        )

@register_action("poll_end", no_return=True)
@lightbulb.di.with_di
async def handle_poll_end(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
) -> None:
    """Handle poll end button click"""
    
    poll_id = action_id
    
    # Get poll data
    poll_data = await mongo.discord_polls.find_one({"_id": poll_id})
    
    if not poll_data:
        await ctx.respond("❌ Poll not found", ephemeral=True)
        return
    
    # Check if user is the creator
    if str(ctx.interaction.user.id) != poll_data["creator_id"]:
        await ctx.respond("❌ Only the poll creator can end the poll", ephemeral=True)
        return
    
    if not poll_data["active"]:
        await ctx.respond("❌ This poll has already ended", ephemeral=True)
        return
    
    # Cancel scheduled job
    try:
        scheduler.remove_job(f"poll_end_{poll_id}")
    except:
        pass
    
    # End the poll
    from . import end_poll as poll_end_func
    await poll_end_func(
        poll_id,
        poll_data["guild_id"],
        poll_data["channel_id"],
        poll_data["message_id"]
    )
    
    # Update ended reason
    await mongo.discord_polls.update_one(
        {"_id": poll_id},
        {"$set": {"ended_reason": "manual"}}
    )
    
    await ctx.respond("✅ Poll ended successfully", ephemeral=True)

@register_action("poll_details", no_return=True)
@lightbulb.di.with_di
async def handle_poll_details(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
) -> None:
    """Handle poll details button click"""
    poll_id = action_id
    
    # Get poll data
    poll_data = await mongo.discord_polls.find_one({"_id": poll_id})
    
    if not poll_data:
        await ctx.respond("❌ Poll not found", ephemeral=True)
        return
    
    # Import and use the show_poll_results function from view.py
    from .view import show_poll_results
    await show_poll_results(ctx, poll_data, bot)