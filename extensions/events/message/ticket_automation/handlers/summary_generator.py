# extensions/events/message/ticket_automation/handlers/summary_generator.py
"""
Generates a comprehensive summary of candidate information after questionnaire completion.
Collects all data from the automation process and formats it nicely.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import hikari

from hikari.impl import (
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)

from utils.mongo import MongoClient
from utils.constants import BLUE_ACCENT
from utils.emoji import emojis
from ..core.state_manager import StateManager

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None


def initialize(mongo: MongoClient, bot: hikari.GatewayBot):
    """Initialize the summary generator"""
    global mongo_client, bot_instance
    mongo_client = mongo
    bot_instance = bot


async def generate_candidate_summary(channel_id: int, user_id: int) -> Optional[List[Container]]:
    """
    Generate a comprehensive summary of all candidate information.
    
    Args:
        channel_id: The ticket channel ID
        user_id: The Discord user ID
    
    Returns:
        List of Container components with the formatted summary
    """
    
    if not mongo_client:
        print("[SummaryGenerator] Error: MongoDB client not initialized")
        return None
    
    try:
        # Get ticket state
        ticket_state = await StateManager.get_ticket_state(str(channel_id))
        if not ticket_state:
            print(f"[SummaryGenerator] No ticket state found for channel {channel_id}")
            return None
        
        # Extract all relevant data
        ticket_info = ticket_state.get("ticket_info", {})
        step_data = ticket_state.get("step_data", {})
        questionnaire_data = step_data.get("questionnaire", {})
        
        # Get player data from new_recruits collection
        main_account = None
        alt_accounts = []
        
        # Query for main account (not an additional account)
        main_account_doc = await mongo_client.new_recruits.find_one({
            "ticket_channel_id": str(channel_id),
            "$or": [
                {"is_additional_account": False},
                {"is_additional_account": {"$exists": False}}
            ]
        })
        
        if main_account_doc:
            main_account = {
                "name": main_account_doc.get("player_name", "Unknown"),
                "tag": main_account_doc.get("player_tag", "Unknown"),
                "th_level": main_account_doc.get("player_th_level", "??")
            }
        
        # Query for additional accounts
        alt_account_cursor = mongo_client.new_recruits.find({
            "ticket_channel_id": str(channel_id),
            "is_additional_account": True
        })
        
        async for alt_doc in alt_account_cursor:
            alt_accounts.append({
                "name": alt_doc.get("player_name", "Unknown"),
                "tag": alt_doc.get("player_tag", "Unknown"),
                "th_level": alt_doc.get("player_th_level", "??")
            })
        
        # Build components list
        components_list = []
        
        # Title
        components_list.append(Text(content="## 📊 **Candidate Summary**"))
        components_list.append(Separator(divider=True))
        
        # Candidate Information Section
        components_list.append(Text(content="### 📋 **Candidate Information**"))
        
        # Discord ID
        discord_id = ticket_info.get("user_id", user_id)
        components_list.append(Text(content=f"**Discord:** <@{discord_id}>"))
        
        # Main Account
        if main_account:
            components_list.append(Text(content="\n**Main Account:**"))
            components_list.append(Text(content=f"  • **Player Name:** {main_account['name']}"))
            components_list.append(Text(content=f"  • **Player Tag:** {main_account['tag']}"))
            components_list.append(Text(content=f"  • **TH Level:** {main_account['th_level']}"))
        else:
            components_list.append(Text(content="**Main Account:** Not found"))
        
        # Additional Accounts
        if alt_accounts:
            components_list.append(Separator(divider=True))
            components_list.append(Text(content="\n**Alt Accounts:**"))
            for i, account in enumerate(alt_accounts, 1):
                components_list.append(Text(content=f"\n  **Account {i}:**"))
                components_list.append(Text(content=f"    • **Player Name:** {account['name']}"))
                components_list.append(Text(content=f"    • **Player Tag:** {account['tag']}"))
                components_list.append(Text(content=f"    • **TH Level:** {account['th_level']}"))
        
        # Personal Information Section
        components_list.append(Separator(divider=True))
        components_list.append(Text(content="### 👤 **Personal Information**"))
        
        # Age Bracket
        age_bracket = questionnaire_data.get("responses", {}).get("age_bracket", "Not provided")
        age_display = {
            "13_17": "13-17 years old",
            "18_24": "18-24 years old", 
            "25_34": "25-34 years old",
            "35_plus": "35+ years old"
        }.get(age_bracket, age_bracket)
        components_list.append(Text(content=f"**Age Bracket:** {age_display}"))
        
        # Timezone
        timezone_info = questionnaire_data.get("responses", {}).get("timezone", "Not provided")
        components_list.append(Text(content=f"**Timezone:** {timezone_info}"))
        
        # Attack Strategies Section
        components_list.append(Separator(divider=True))
        components_list.append(Text(content="### ⚔️ **Attack Strategies**"))
        
        attack_summary = questionnaire_data.get("attack_summary", "")
        if attack_summary:
            # Format the summary with proper emojis
            formatted_attack = attack_summary.replace("{red_arrow}", str(emojis.red_arrow_right))
            formatted_attack = formatted_attack.replace("{white_arrow}", str(emojis.white_arrow_right))
            formatted_attack = formatted_attack.replace("{blank}", str(emojis.blank))
            components_list.append(Text(content=formatted_attack))
        else:
            components_list.append(Text(content=f"{emojis.blank}{emojis.white_arrow_right} No strategies provided"))
        
        # Clan Expectations Section
        components_list.append(Separator(divider=True))
        components_list.append(Text(content="### 🏰 **Clan Expectations**"))
        
        expectations_summary = questionnaire_data.get("expectations_summary", "")
        if expectations_summary:
            # Format the summary with proper emojis
            formatted_expectations = expectations_summary.replace("{red_arrow}", str(emojis.red_arrow_right))
            formatted_expectations = formatted_expectations.replace("{white_arrow}", str(emojis.white_arrow_right))
            formatted_expectations = formatted_expectations.replace("{blank}", str(emojis.blank))
            components_list.append(Text(content=formatted_expectations))
        else:
            components_list.append(Text(content=f"{emojis.blank}{emojis.white_arrow_right} No expectations provided"))
        
        # Footer
        components_list.append(Separator(divider=True))
        components_list.append(Text(content=f"-# Summary generated at <t:{int(datetime.now(timezone.utc).timestamp())}:F>"))
        components_list.append(Media(items=[MediaItem(media="assets/Blue_Footer.png")]))
        
        # Create container
        return [
            Container(
                accent_color=BLUE_ACCENT,
                components=components_list
            )
        ]
        
    except Exception as e:
        print(f"[SummaryGenerator] Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        return None


async def send_candidate_summary(channel_id: int, thread_id: int, user_id: int) -> bool:
    """
    Generate and send the candidate summary to the ticket thread.
    
    Args:
        channel_id: The ticket channel ID
        thread_id: The thread ID to send the summary to
        user_id: The Discord user ID
        
    Returns:
        True if successful, False otherwise
    """
    
    if not bot_instance:
        print("[SummaryGenerator] Error: Bot instance not initialized")
        return False
    
    try:
        # Generate the summary components
        summary_components = await generate_candidate_summary(channel_id, user_id)
        if not summary_components:
            print("[SummaryGenerator] Failed to generate summary components")
            return False
        
        # Send to the thread
        await bot_instance.rest.create_message(
            channel=thread_id,
            components=summary_components
        )
        
        # Send recruitment lead ping as a separate message
        await bot_instance.rest.create_message(
            channel=thread_id,
            content="<@&1039311270614142977> Automated interview complete! Run `/recruit bidding` for the appropriate user accounts.",
            role_mentions=True
        )
        
        print(f"[SummaryGenerator] Sent candidate summary and recruitment lead ping to thread {thread_id}")
        return True
        
    except Exception as e:
        print(f"[SummaryGenerator] Error sending summary: {e}")
        import traceback
        traceback.print_exc()
        return False