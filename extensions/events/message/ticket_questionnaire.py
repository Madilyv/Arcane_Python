# extensions/events/message/ticket_questionnaire.py
"""
Ticket questionnaire automation system with AI-powered attack strategy processing.

Features:
- Interview process selection (Bot-driven vs Speak with Recruiter)
- AI-powered attack strategies analysis using Claude
- Automation halt functionality for manual takeover
- Sequential question flow management
"""

import os
import asyncio
import aiohttp
import json
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
from utils.ai_prompts import ATTACK_STRATEGIES_PROMPT

# Configuration
RECRUITMENT_STAFF_ROLE = 999140213953671188  # Note: Role ID as integer, not string
LOG_CHANNEL_ID = 1345589195695194113

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Global variables
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
loader = lightbulb.Loader()


async def process_attack_strategies_with_ai(existing_summary: str, new_input: str) -> str:
    """Process attack strategies using Claude AI"""

    # The system prompt from your document
    system_prompt = """You are an assistant summarizing and refining a user's attack strategies for their main village and Clan Capital in the game Clash of Clans. You will receive two types of input: the existing summary and new user input. Your goal is to integrate the new user input into the existing summary without losing any previously stored information.

CRITICAL RULES - VIOLATION OF THESE WILL CAUSE SYSTEM FAILURE:
1. NEVER add commentary, feedback, or explanatory text in the output
2. ONLY output the strategies themselves as bullet points  
3. Capital Hall levels go in "Familiarity" section ONLY, never in strategy descriptions
4. Each strategy should be a clean, simple description without any meta-commentary
5. DO NOT explain what you did with the data - just output the updated list

If the new input is invalid or provides no new valid strategies, return the original summary unchanged (if it exists). Only display "No input provided." if there was no existing data at all and the user provided nothing valid.

### Troop List Categorization:
- **Main Village Troops:**
  - Elixir Troops: Barbarian, Archer, Giant, Goblin, Wall Breaker, Balloon, Wizard, Healer, Dragon, P.E.K.K.A, Baby Dragon, Miner, Electro Dragon, Yeti, Dragon Rider, Electro Titan, Root Rider, Thrower.
  - Dark Elixir Troops: Minion, Hog Rider, Valkyrie, Golem, Witch, Lava Hound, Bowler, Ice Golem, Headhunter, Apprentice Warden, Druid.
  - Super Troops: Super Barbarian, Super Archer, Super Giant, Sneaky Goblin, Super Wall Breaker, Rocket Balloon, Super Wizard, Super Dragon, Inferno Dragon, Super Minion, Super Valkyrie, Super Witch, Ice Hound, Super Bowler, Super Miner, Super Hog Rider.

- **Clan Capital Troops:**
  - Super Barbarian, Sneaky Archers, Super Giant, Battle Ram, Minion Horde, Super Wizard, Rocket Balloons, Skeleton Barrels, Flying Fortress, Raid Cart, Power P.E.K.K.A, Hog Raiders, Super Dragon, Mountain Golem, Inferno Dragon, Super Miner, Mega Sparky.

### Hero and Equipment Recognition:
- **Main Village Heroes:** Barbarian King, Archer Queen, Grand Warden, Royal Champion, Minion Prince
- **Hero Equipment:**
  - Barbarian King: Barbarian Puppet, Rage Vial, Earthquake Boots, Vampstache, Giant Gauntlet, Spiky Ball
  - Archer Queen: Archer Puppet, Invisibility Vial, Giant Arrow, Healer Puppet, Frozen Arrow, Magic Mirror
  - Minion Prince: Henchmen Puppet, Dark Orb
  - Grand Warden: Eternal Tome, Life Gem, Rage Gem, Healing Tome, Fireball, Lavaloon Puppet
  - Royal Champion: Royal Gem, Seeking Shield, Hog Rider Puppet, Haste Vial, Rocket Spear, Electro Boots

If a hero or hero equipment is mentioned alongside other main village troops or strategies in the same line, treat them as one combined strategy.

### Strategy and Input Mapping Rules:
1. **Identify Valid Input:**
   - Parse new input for mentions of known strategies (e.g., 'Hybrid', 'Hydra', 'Lalo', 'Blizzard Lalo'), main village troops, heroes, and hero equipment.
   - Recognize 'cap' or 'capital' followed by a number as 'Capital Hall number' (no brackets).
   - If 'cap' or 'capital' is mentioned without a number, try to associate it with the most recently known Capital Hall level.
   - If a troop is mentioned with capital context but not a Clan Capital troop, attempt a valid mapping (e.g., Miner → Super Miner) or ignore if no mapping is possible.

   **Context Clues for Clan Capital:**
   - "Miners with freeze" or "Miners freeze" → Clan Capital strategy (Super Miners)
   - Any mention of "freeze" with troops typically indicates Clan Capital
   - "Rocket Balloons", "Flying Fortress", "Mountain Golem", "Mega Sparky" → Always Clan Capital
   - If ambiguous, consider common usage: Miners with spells = usually Clan Capital

2. **Categorization Logic:**
   - **Main Village Strategies:**
     - Any single user input line that includes recognized main village strategies, troops, heroes, and/or hero equipment forms one bullet point.
     - Common main village strategies: Hybrid, Hydra, LaLo, Queen Charge, Blizzard, Smash attacks
     - Example:
       - "Warden with Fireball and Superwitches" → One bullet point: "Warden with Fireball and Superwitches"
       - "Queen Charge Hydra" → Another bullet: "Queen Charge Hydra"

   - **Clan Capital Strategies:**
     - List ONLY the strategy itself, NO Capital Hall numbers in the bullet point
     - When user says "Miners freeze in Capital Hall 8", output: "Miners Freeze" (NOT "Miners Freeze in Capital Hall 8")
     - Capital Hall numbers ONLY go in the Familiarity section
     - Common capital strategies: "Miners freeze", "Super wizard spam", "Mountain golem tanking"

   - Ignore invalid input without altering previously stored data.

3. **Data Retention and Updates:**
   - Use existing summary as baseline.
   - If new input is valid, append one bullet point per user input line.
   - If no valid additions, do not alter the existing summary.
   - NEVER add explanatory text like "has been integrated" or "new input added"

4. **Familiarity with Clan Capital Levels:**
   - Extract ALL Capital Hall numbers mentioned and track them here
   - Update lowest-highest range if new levels appear
   - Example: If user says "Miners freeze cap 8", add 8 to the range
   - Display ONLY: "Familiar with Capital Hall 7-10" format
   - NEVER add any other text besides the range
   - If no levels mentioned: "No input provided."

5. **No Destructive Updates:**
   - Never remove previously known strategies.
   - Ignore invalid input.
   - NEVER add meta-commentary about the update process

6. **Formatting the Final Output:**
   - Each user input line that results in a valid strategy is one bullet point.
   - No brackets around Capital Hall numbers.
   - NO FEEDBACK OR COMMENTARY TEXT
   - If no entries for a category, say **No input provided.**

**Final Output Sections (EXACT FORMAT - NO MODIFICATIONS):**

{red_arrow} **Main Village Strategies:**
{blank}{white_arrow} Strategy 1
{blank}{white_arrow} Strategy 2
(or if none: No input provided.)

{red_arrow} **Clan Capital Strategies:**
{blank}{white_arrow} Strategy 1 (NO capital hall numbers here)
{blank}{white_arrow} Strategy 2 (NO capital hall numbers here)
(or if none: No input provided.)

{red_arrow} **Familiarity with Clan Capital Levels:**
{blank}{white_arrow} Familiar with Capital Hall X-Y (ONLY the range, nothing else)
(or if none: No input provided.)

REMEMBER:
- Output ONLY the strategies and ranges
- NO commentary about integration or updates
- NO explanatory text
- Capital Hall numbers ONLY in Familiarity section

**Example of CORRECT output:**

{red_arrow} **Main Village Strategies:**
{blank}{white_arrow} RC Charge with Invis
{blank}{white_arrow} Queen Charge
{blank}{white_arrow} Dragon Riders with RC Charge

{red_arrow} **Clan Capital Strategies:**
{blank}{white_arrow} Miners Freeze

{red_arrow} **Familiarity with Clan Capital Levels:**
{blank}{white_arrow} Familiar with Capital Hall 8

**Common Classifications to Remember:**
- "Miners with freeze" or "Miners freeze" → ALWAYS Clan Capital: "{blank}{white_arrow} Miners Freeze"
- "Miners freeze cap 8" → Capital: "{blank}{white_arrow} Miners Freeze", Familiarity: includes 8 in range
- "RC Charge" or "Queen Charge" → Main Village (these are heroes)
- "Dragon Riders with RC Charge" → Main Village (RC = Royal Champion hero)
- NEVER include Capital Hall numbers in strategy bullets - they go in Familiarity section only
- NEVER add commentary like "has been integrated" or "strategy has been retained"
- NEVER add explanatory text about what happened to the data"""

    # Replace placeholders with actual values
    system_prompt = system_prompt.replace("{red_arrow}", "➤")  # Placeholder for formatting
    system_prompt = system_prompt.replace("{blank}{white_arrow}", "  ➤")  # Placeholder for formatting

    user_prompt = f"Original Summary: {existing_summary}\nFeedback: {new_input}"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": "claude-3-haiku-20240307",  # Fast and cost-effective for this use case
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "system": system_prompt
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["content"][0]["text"]
                else:
                    print(f"[Questionnaire] Claude API error: {response.status}")
                    return existing_summary or "Error processing strategies. Please try again."
    except Exception as e:
        print(f"[Questionnaire] Error calling Claude API: {e}")
        return existing_summary or "Error processing strategies. Please try again."


async def create_attack_strategy_components(summary: str, title: str, show_done_button: bool = True):
    """Create components for attack strategy display"""

    # Parse the summary to extract sections
    main_village = "No input provided."
    clan_capital = "No input provided."
    capital_levels = "No input provided."

    if summary:
        lines = summary.split('\n')
        current_section = None
        main_village_strategies = []
        clan_capital_strategies = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "Main Village Strategies:" in line:
                current_section = "main"
                continue
            elif "Clan Capital Strategies:" in line:
                current_section = "capital"
                continue
            elif "Familiarity with Clan Capital Levels:" in line:
                current_section = "levels"
                continue

            # Clean up the line - remove existing formatting
            if line and current_section:
                # Remove existing arrows and bullets
                clean_line = line
                if "➤" in clean_line:
                    clean_line = clean_line.split("➤", 1)[-1].strip()
                if clean_line.startswith('•'):
                    clean_line = clean_line[1:].strip()

                if clean_line and clean_line != "No input provided.":
                    if current_section == "main":
                        main_village_strategies.append(clean_line)
                    elif current_section == "capital":
                        clan_capital_strategies.append(clean_line)
                    elif current_section == "levels":
                        capital_levels = clean_line

        # Format the sections with proper emojis
        if main_village_strategies:
            main_village = "\n".join(
                [f"{emojis.blank}{emojis.white_arrow_right} {strategy}" for strategy in main_village_strategies])

        if clan_capital_strategies:
            clan_capital = "\n".join(
                [f"{emojis.blank}{emojis.white_arrow_right} {strategy}" for strategy in clan_capital_strategies])

        if capital_levels != "No input provided.":
            capital_levels = f"{emojis.blank}{emojis.white_arrow_right} {capital_levels}"

    # Build components list
    components_list = [
        Text(content=title),
        Separator(divider=True, spacing=hikari.SpacingType.SMALL),

        # Main Village Strategies
        Text(content=f"{emojis.red_arrow_right} **Main Village Strategies:**"),
        Text(content=main_village),

        Separator(divider=True, spacing=hikari.SpacingType.SMALL),

        # Clan Capital Strategies
        Text(content=f"{emojis.red_arrow_right} **Clan Capital Strategies:**"),
        Text(content=clan_capital),

        Separator(divider=True, spacing=hikari.SpacingType.SMALL),

        # Capital Levels
        Text(content=f"{emojis.red_arrow_right} **Familiarity with Clan Capital Levels:**"),
        Text(content=capital_levels),

        Separator(divider=True, spacing=hikari.SpacingType.LARGE),
    ]

    # Only add the instruction and button if show_done_button is True
    if show_done_button:
        components_list.extend([
            Text(content="_Continue typing to add more strategies, or click Done when finished._"),
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        custom_id=f"attack_strategies_done:",
                        label="Done",
                        emoji="✅"
                    )
                ]
            ),
        ])

    # Always add the footer
    components_list.append(Media(items=[MediaItem(media="assets/Red_Footer.png")]))

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=components_list
        )
    ]

    return components


async def send_attack_strategies(channel_id: int, user_id: int):
    """Send the attack strategies question with AI processing"""

    try:
        # Get ticket state
        ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        if not ticket_state:
            print(f"[Questionnaire] No ticket state found for channel {channel_id}")
            return

        question_key = "attack_strategies"
        question_data = QUESTIONNAIRE_QUESTIONS[question_key]

        # Set up state for collecting strategies
        update_result = await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "step_data.questionnaire.current_question": question_key,
                    "step_data.questionnaire.awaiting_response": True,
                    "step_data.questionnaire.attack_summary": "",  # Initialize summary
                    "step_data.questionnaire.collecting_strategies": True  # Flag for continuous collection
                }
            }
        )

        print(
            f"[Questionnaire] Set collecting_strategies=True for channel {channel_id}, modified: {update_result.modified_count}")

        # Verify the update
        updated_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
        collecting_flag = updated_state.get("step_data", {}).get("questionnaire", {}).get("collecting_strategies",
                                                                                          False)
        print(f"[Questionnaire] Verified collecting_strategies={collecting_flag} for channel {channel_id}")

        # Create initial components with empty summary
        components = await create_attack_strategy_components("", question_data["title"])

        channel = await bot_instance.rest.fetch_channel(channel_id)
        msg = await channel.send(components=components)

        # Store message ID
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {"$set": {f"messages.questionnaire_{question_key}": str(msg.id)}}
        )

        print(f"[Questionnaire] Sent attack strategies question with AI to channel {channel_id}, msg_id: {msg.id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending attack strategies: {e}")
        import traceback
        traceback.print_exc()


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
                        "*Your choice, your journey!* 🚀"
                    )),
                    ActionRow(
                        components=[
                            Button(
                                style=hikari.ButtonStyle.PRIMARY,
                                custom_id=f"select_bot_interview:{channel_id}_{user_id}",
                                label="Bot-Driven Interview",
                                emoji="🤖"
                            ),
                            Button(
                                style=hikari.ButtonStyle.SECONDARY,
                                custom_id=f"select_recruiter_interview:{channel_id}_{user_id}",
                                label="Speak with Recruiter",
                                emoji="👤"
                            ),
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")])
                ]
            )
        ]

        # Send the message
        message = await bot_instance.rest.create_message(
            channel=channel_id,
            components=components
        )

        # Store message ID in MongoDB
        await mongo_client.ticket_automation_state.update_one(
            {"_id": str(channel_id)},
            {
                "$set": {
                    "messages.interview_selection": message.id,
                    "step_data.questionnaire.awaiting_selection": True
                }
            }
        )

        print(f"[Questionnaire] Sent interview selection prompt to channel {channel_id}")

    except Exception as e:
        print(f"[Questionnaire] Error sending interview selection: {e}")
        import traceback
        traceback.print_exc()


@register_action("select_recruiter_interview", no_return=True)
@lightbulb.di.with_di
async def handle_recruiter_interview_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle selection of recruiter interview"""

    channel_id, user_id = action_id.split("_")

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ You cannot interact with this ticket. This is not your recruitment process.",
            ephemeral=True
        )
        return

    # Update the message to show selection
    confirmation_components = [
        Container(
            accent_color=GREEN_ACCENT,
            components=[
                Text(content="## ✅ **Recruiter Interview Selected!**"),
                Text(content=(
                    "Perfect! A recruiter will be with you shortly.\n"
                    f"I've pinged <@&{RECRUITMENT_STAFF_ROLE}> to let them know you're ready.\n\n"
                    "*Hang tight - someone will be with you soon!*"
                )),
                Media(items=[MediaItem(media="assets/Green_Footer.png")])
            ]
        )
    ]

    await ctx.interaction.edit_initial_response(components=confirmation_components)

    # Send a message pinging the recruitment staff
    await ctx.get_channel().send(
        f"<@&{RECRUITMENT_STAFF_ROLE}> - <@{user_id}> has requested a one-on-one interview!"
    )

    # Update MongoDB to halt automation
    from utils.ticket_state import TicketState
    halt_update = TicketState.halt_automation(
        reason="User selected recruiter interview",
        details={"selected_by": int(user_id)}
    )

    # Add interview type to the update
    halt_update["$set"]["step_data.questionnaire.interview_type"] = "recruiter"

    await mongo.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        halt_update
    )

    # Log to recruitment channel
    if LOG_CHANNEL_ID:
        try:
            log_channel = await ctx.bot.rest.fetch_channel(LOG_CHANNEL_ID)
            await log_channel.send(
                f"📋 **Interview Type Selected**\n"
                f"User: <@{user_id}>\n"
                f"Channel: <#{channel_id}>\n"
                f"Type: **Recruiter Interview**\n"
                f"Status: Automation halted, waiting for recruiter"
            )
        except:
            pass


@register_action("select_bot_interview", no_return=True)
@lightbulb.di.with_di
async def handle_bot_interview_selection(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    """Handle selection of bot-driven interview"""

    channel_id, user_id = action_id.split("_")

    # Verify this is the correct user
    if ctx.user.id != int(user_id):
        await ctx.respond(
            "❌ You cannot interact with this ticket. This is not your recruitment process.",
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

    # Send first question (attack strategies) with AI
    await send_attack_strategies(int(channel_id), int(user_id))


# Handler for the Done button on attack strategies
@register_action("attack_strategies_done", no_return=True)
async def handle_attack_strategies_done(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Handle when user clicks Done on attack strategies"""

    channel_id = ctx.channel_id
    user_id = ctx.user.id

    # Verify this is the correct user
    ticket_state = await mongo_client.ticket_automation_state.find_one({"_id": str(channel_id)})
    if not ticket_state:
        await ctx.respond("❌ Ticket state not found.", ephemeral=True)
        return

    # Check multiple possible locations for user ID and handle type conversion
    stored_user_id = (
            ticket_state.get("discord_id") or
            ticket_state.get("ticket_info", {}).get("user_id") or
            ticket_state.get("user_id")
    )

    # Convert to int for comparison if it's stored as string
    if stored_user_id:
        try:
            stored_user_id = int(stored_user_id)
        except (ValueError, TypeError):
            print(f"[Questionnaire] Error converting user_id: {stored_user_id}")
            pass

    if not stored_user_id or user_id != stored_user_id:
        print(f"[Questionnaire] User ID mismatch: {user_id} != {stored_user_id}")
        await ctx.respond("❌ You cannot interact with this ticket.", ephemeral=True)
        return

    # Stop collecting strategies
    await mongo_client.ticket_automation_state.update_one(
        {"_id": str(channel_id)},
        {
            "$set": {
                "step_data.questionnaire.collecting_strategies": False,
                "step_data.questionnaire.awaiting_response": False
            }
        }
    )

    # Get the current attack summary to display
    current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

    # Create the same components but without the Done button
    final_components = await create_attack_strategy_components(
        current_summary,
        QUESTIONNAIRE_QUESTIONS["attack_strategies"]["title"],
        show_done_button=False  # Add parameter to hide button
    )

    # Update the message to remove the Done button (interaction already deferred by component_handler)
    await ctx.interaction.edit_initial_response(components=final_components)

    # Wait and move to next question
    await asyncio.sleep(2)

    # Move to next question
    next_question = QUESTIONNAIRE_QUESTIONS["attack_strategies"]["next"]
    if next_question:
        await send_questionnaire_question(channel_id, user_id, next_question)

    print(f"[Questionnaire] User {user_id} completed attack strategies")


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
            "{blank}{white_arrow} _e.g. Crystal, Masters, Champions_\n\n"
            "*The more specific, the better we can match you!*"
        ),
        "next": "discord_basic_skills"
    },
    "discord_basic_skills": {
        "title": "## 💬 **Discord Basic Skills Check**",
        "content": (
            "Quick Discord skills check! Show us you can:\n\n"
            "**1.** Add a reaction to this message\n"
            "**2.** Reply and mention someone\n\n"
            "*These are essential for clan communication!*"
        ),
        "next": "discord_basic_skills_2",
        "requires_reaction": True,
        "requires_mention": True
    },
    "discord_basic_skills_2": {
        "title": "## 🔊 **Voice Channel Experience**",
        "content": (
            "Tell us about your Discord voice experience:\n\n"
            "{red_arrow} **Have you used Discord voice channels before?**\n"
            "{blank}{white_arrow} _Yes/No_\n\n"
            "{red_arrow} **Are you comfortable joining voice calls for wars?**\n"
            "{blank}{white_arrow} _Always/Sometimes/Text only_\n\n"
            "*Voice communication helps during coordinated attacks!*"
        ),
        "next": "age_bracket_timezone",
        "has_gif": True,
        "gif_url": "https://tenor.com/view/voice-call-discord-mod-discord-kitten-gif-26050621"
    },
    "age_bracket_timezone": {
        "title": "## 📊 **Demographics & Availability**",
        "content": (
            "Just a couple more quick details:\n\n"
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
        # Special handling for attack strategies with AI
        if question_key == "attack_strategies":
            await send_attack_strategies(channel_id, user_id)
            return

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

    # Verify message is from ticket creator first
    if "discord_id" in ticket_state and event.author_id != ticket_state["discord_id"]:
        return

    # PRIORITY CHECK: Are we collecting attack strategies?
    if (ticket_state.get("step_data", {}).get("questionnaire", {}).get("collecting_strategies", False)):

        # Check if message is from the right user - try multiple locations and handle type conversion
        expected_user_id = (
                ticket_state.get("discord_id") or
                ticket_state.get("ticket_info", {}).get("user_id") or
                ticket_state.get("user_id")
        )

        # Convert to int for comparison if it's stored as string
        if expected_user_id:
            try:
                expected_user_id = int(expected_user_id)
            except (ValueError, TypeError):
                print(f"[Questionnaire] Error converting user_id: {expected_user_id}")
                expected_user_id = None

        if expected_user_id and event.author_id != expected_user_id:
            print(f"[Questionnaire] Ignoring message from wrong user: {event.author_id} != {expected_user_id}")
            return

        print(f"[Questionnaire] Processing attack strategy from user {event.author_id}: {event.content}")

        # Get current summary
        current_summary = ticket_state.get("step_data", {}).get("questionnaire", {}).get("attack_summary", "")

        # Process with AI
        new_summary = await process_attack_strategies_with_ai(current_summary, event.content)

        # Update database with new summary
        await mongo_client.ticket_automation_state.update_one(
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
                await bot_instance.rest.edit_message(event.channel_id, int(msg_id), components=components)
                print(f"[Questionnaire] Updated attack strategy display")
            except Exception as e:
                print(f"[Questionnaire] Error updating attack strategy message: {e}")
                import traceback
                traceback.print_exc()

        # Delete the user's message to keep channel clean
        try:
            await event.message.delete()
        except:
            pass  # Ignore if we can't delete

        return  # IMPORTANT: Exit here, don't process as normal response

    # Check if we're in questionnaire step and awaiting response
    if (ticket_state.get("automation_state", {}).get("current_step") != "questionnaire" or
            not ticket_state.get("step_data", {}).get("questionnaire", {}).get("awaiting_response") or
            ticket_state.get("automation_state", {}).get("status") == "halted"):
        return

    # Verify message is from ticket creator (double check)
    if "ticket_info" in ticket_state and event.author_id != int(ticket_state["ticket_info"]["user_id"]):
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
        print("Questionnaire automation system with AI initialized")