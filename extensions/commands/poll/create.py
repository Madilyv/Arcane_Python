# extensions/commands/poll/create.py
"""
Create polls with duration and role ping options.
"""

import hikari
import lightbulb
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT, GOLD_ACCENT, GREEN_ACCENT, MAGENTA_ACCENT
from extensions.components import register_action
from . import loader, poll, scheduler

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    InteractiveButtonBuilder as Button,
    MessageActionRowBuilder as ActionRow,
    ModalActionRowBuilder as ModalActionRow,
    SectionComponentBuilder as Section,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from apscheduler.triggers.date import DateTrigger

# Duration choices
DURATION_CHOICES = [
    ("5 minutes", 5),
    ("15 minutes", 15),
    ("30 minutes", 30),
    ("1 hour", 60),
    ("2 hours", 120),
    ("4 hours", 240),
    ("8 hours", 480),
    ("12 hours", 720),
    ("24 hours", 1440),
]

@poll.register()
class Create(
    lightbulb.SlashCommand,
    name="create",
    description="Create a new poll with multiple options",
):
    duration = lightbulb.string(
        "duration",
        "How long should the poll run?",
        choices=[
            lightbulb.Choice(name=name, value=name)
            for name, _ in DURATION_CHOICES
        ]
    )
    
    role = lightbulb.role(
        "role",
        "Role to ping for the poll (optional)",
        default=None
    )
    
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ) -> None:
        # Get duration in minutes
        duration_minutes = next(minutes for name, minutes in DURATION_CHOICES if name == self.duration)
        
        # Store data for modal response
        poll_data = {
            "duration_minutes": duration_minutes,
            "role_id": str(self.role.id) if self.role else None,
            "channel_id": str(ctx.channel_id),
            "guild_id": str(ctx.guild_id),
            "creator_id": str(ctx.user.id),
        }
        
        # Create modal
        modal_rows = [
            ModalActionRow().add_text_input(
                "title",
                "Poll Title",
                placeholder="Enter a catchy title for your poll",
                required=True,
                max_length=100
            ),
            ModalActionRow().add_text_input(
                "description",
                "Poll Description",
                placeholder="What are you asking about?",
                required=True,
                style=hikari.TextInputStyle.PARAGRAPH,
                max_length=500
            ),
            ModalActionRow().add_text_input(
                "option1",
                "Option 1",
                placeholder="First choice",
                required=True,
                max_length=80
            ),
            ModalActionRow().add_text_input(
                "option2", 
                "Option 2",
                placeholder="Second choice",
                required=True,
                max_length=80
            ),
            ModalActionRow().add_text_input(
                "option3",
                "Option 3 (Optional)",
                placeholder="Third choice (leave blank if not needed)",
                required=False,
                max_length=80
            ),
        ]
        
        # Store poll data temporarily
        await mongo.button_store.insert_one({
            "_id": str(ctx.interaction.id),
            "type": "poll_create",
            "data": poll_data,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        })
        
        await ctx.respond_with_modal(
            title="Create Poll",
            custom_id=f"poll_modal:{ctx.interaction.id}",
            components=modal_rows
        )

@register_action("poll_modal", is_modal=True, no_return=True)
@lightbulb.di.with_di
async def handle_poll_modal(
    ctx: lightbulb.components.ModalContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
) -> None:
    """Handle poll creation modal submission"""
    
    # Get stored poll data
    stored = await mongo.button_store.find_one({"_id": action_id})
    if not stored:
        await ctx.respond("❌ Poll creation expired. Please try again.", ephemeral=True)
        return
    
    poll_data = stored["data"]
    
    # Extract modal values
    values = {}
    for row in ctx.interaction.components:
        for comp in row:
            values[comp.custom_id] = comp.value
    
    # Build options list with better emojis
    options = []
    emojis = ["🥇", "🥈", "🥉"]
    # All vote buttons will be secondary style for cleaner look
    colors = [hikari.ButtonStyle.SECONDARY, hikari.ButtonStyle.SECONDARY, 
              hikari.ButtonStyle.SECONDARY]
    
    for i in range(1, 4):  # Only 3 options now
        option_text = values.get(f"option{i}", "").strip()
        if option_text:
            options.append({
                "id": i,
                "text": option_text,
                "emoji": emojis[i-1],
                "color": colors[i-1]
            })
    
    # Create poll ID
    poll_id = f"poll_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    
    # Calculate end time (ensure timezone.utc for both)
    created_at = datetime.now(timezone.utc)
    ends_at = created_at + timedelta(minutes=poll_data["duration_minutes"])
    
    # Create stunning visual poll components
    poll_components = []
    
    # Header section with role ping if applicable
    header_components = []
    
    # Add role ping at the top if specified
    if poll_data['role_id']:
        header_components.append(Text(content=f"📢 <@&{poll_data['role_id']}> **New poll!**"))
        header_components.append(Separator(divider=True))
    
    header_components.extend([
        Text(content=f"## 📊 {values['title']}"),
        Text(content=f"*{values['description']}*"),
        Separator(divider=False),
        Text(content=(
            f"👤 **Created by:** <@{poll_data['creator_id']}> • "
            f"⏰ **Ends:** <t:{int(ends_at.timestamp())}:R>"
        )),
        Separator(divider=True)
    ])
    
    # Add each option with beautiful progress bars
    for option in options:
        # Create empty progress bar with gradient effect
        progress_bar = "░" * 20  # Longer bars for better visual
        
        poll_components.append(Text(content=f"{option['emoji']} **{option['text']}**"))
        poll_components.append(Text(content=f"`[{progress_bar}]` **0%** (0 votes)"))
        poll_components.append(Text(content="*No votes yet*"))
        poll_components.append(Separator(divider=False))
    
    poll_components.append(Separator(divider=True))
    
    # Add stats footer before image
    poll_components.append(
        Text(content=f"**Total votes:** 0 • **Status:** 🟢 Live")
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
            custom_id=f"poll_end:{poll_id}",
            emoji="🛑"
        )
    )
    control_row.add_component(
        Button(
            style=hikari.ButtonStyle.SECONDARY,
            label="View Details",
            custom_id=f"poll_details:{poll_id}",
            emoji="📊"
        )
    )
    poll_components.append(control_row)
    
    # Create vote buttons SECOND
    vote_buttons = []
    for option in options:
        vote_buttons.append(
            Button(
                style=option['color'],
                emoji=option['emoji'],
                custom_id=f"poll_vote:{poll_id}:{option['id']}"
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
    
    # Send the poll (with role mentions enabled in container if needed)
    message = await bot.rest.create_message(
        channel=int(poll_data['channel_id']),
        components=[container],
        role_mentions=True if poll_data['role_id'] else False
    )
    
    # Save poll to database
    poll_doc = {
        "_id": poll_id,
        "guild_id": poll_data["guild_id"],
        "channel_id": poll_data["channel_id"],
        "message_id": str(message.id),
        "creator_id": poll_data["creator_id"],
        "created_at": created_at,
        "ends_at": ends_at,
        "duration_minutes": poll_data["duration_minutes"],
        "ping_role_id": poll_data["role_id"],
        "title": values["title"],
        "description": values["description"],
        "options": options,
        "votes": {},  # user_id: option_id
        "active": True,
        "ended_reason": None
    }
    
    await mongo.discord_polls.insert_one(poll_doc)
    
    # Schedule poll end
    from . import end_poll as poll_end_func
    scheduler.add_job(
        poll_end_func,
        trigger=DateTrigger(run_date=ends_at),
        args=[poll_id, poll_data["guild_id"], poll_data["channel_id"], str(message.id)],
        id=f"poll_end_{poll_id}",
        replace_existing=True
    )
    
    # Clean up button store
    await mongo.button_store.delete_one({"_id": action_id})
    
    # Respond to interaction
    await ctx.respond(
        f"✅ Poll created successfully! It will end <t:{int(ends_at.timestamp())}:R>",
        ephemeral=True
    )

loader.command(Create)