# extensions/events/message/ticket_automation/handlers/summary_generator.py
"""
Generates a comprehensive summary of candidate information after questionnaire completion.
Collects all data from the automation process and formats it nicely.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import hikari
import coc

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


async def check_candidate_in_family_clans(channel_id: int) -> List[Dict[str, Any]]:
    """
    Check if candidate's accounts are already in any family clans.

    Args:
        channel_id: The ticket channel ID

    Returns:
        List of matches with player and clan details. Empty list if no matches or on error.
        Each match: {
            "player_name": str,
            "player_tag": str,
            "clan_name": str,
            "clan_tag": str,
            "leader_id": int,
            "leader_role_id": int
        }
    """
    if not mongo_client:
        print("[SummaryGenerator] MongoDB client not initialized")
        return []

    try:
        # Get CoC client from bot_data
        from utils import bot_data
        coc_client = bot_data.data.get("coc_client")
        if not coc_client:
            print("[SummaryGenerator] CoC client not available")
            return []

        # Get all recruit accounts for this ticket
        recruits = await mongo_client.new_recruits.find({
            "ticket_channel_id": str(channel_id)
        }).to_list(length=None)

        if not recruits:
            print(f"[SummaryGenerator] No recruits found for channel {channel_id}")
            return []

        # Get all family clans
        family_clans = await mongo_client.clans.find().to_list(length=None)
        if not family_clans:
            print("[SummaryGenerator] No family clans found in database")
            return []

        # Create lookup dict: clan_tag -> clan_data
        family_clan_lookup = {clan["tag"]: clan for clan in family_clans}

        matches = []

        # Check each recruit account
        for recruit in recruits:
            player_tag = recruit.get("player_tag")
            if not player_tag:
                continue

            try:
                # Get player from CoC API
                player = await coc_client.get_player(player_tag)

                # Check if player is in a clan and if that clan is in our family
                if player.clan and player.clan.tag in family_clan_lookup:
                    clan_data = family_clan_lookup[player.clan.tag]
                    matches.append({
                        "player_name": player.name,
                        "player_tag": player.tag,
                        "clan_name": clan_data.get("name", player.clan.name),
                        "clan_tag": player.clan.tag,
                        "leader_id": clan_data.get("leader_id"),
                        "leader_role_id": clan_data.get("leader_role_id")
                    })

            except coc.NotFound:
                print(f"[SummaryGenerator] Player not found: {player_tag}")
                continue
            except Exception as e:
                print(f"[SummaryGenerator] Error checking player {player_tag}: {e}")
                continue

        return matches

    except Exception as e:
        print(f"[SummaryGenerator] Error in check_candidate_in_family_clans: {e}")
        import traceback
        traceback.print_exc()
        return []


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

        # Check if candidate is already in family clans
        matches = await check_candidate_in_family_clans(channel_id)

        # Build dynamic message based on results
        if matches:
            # Found in family clan(s) - send alert with specific details
            alert_lines = ["⚠️ **ALERT:** The following account(s) are already in family clans:\n"]
            for match in matches:
                alert_lines.append(f"• **{match['player_name']}** (`{match['player_tag']}`) is in **{match['clan_name']}**")
                if match.get('leader_id') and match.get('leader_role_id'):
                    alert_lines.append(f"  → Contact: <@{match['leader_id']}> and <@&{match['leader_role_id']}>")
                alert_lines.append("")

            alert_lines.append("Please coordinate with their current clan leadership before proceeding.\n")
            alert_lines.append("Run `/recruit bidding` only after resolving these conflicts.")

            notification_content = "<@&1039311270614142977> **Automated interview complete!**\n\n" + "\n".join(alert_lines)
        else:
            # Not found in any family clan or API failed - send success/fallback message
            # Check if we had an API error by trying a quick check
            from utils import bot_data
            coc_client = bot_data.data.get("coc_client")

            if coc_client:
                # API available - they're not in any family clan
                notification_content = (
                    "<@&1039311270614142977> **Automated interview complete!**\n\n"
                    "✅ **Verification Complete:** Candidate is not currently in any family clan.\n\n"
                    "Proceed with `/recruit bidding` for the appropriate user accounts."
                )
            else:
                # API unavailable - fallback to manual check
                notification_content = (
                    "<@&1039311270614142977> **Automated interview complete!**\n\n"
                    "⚠️ **Unable to verify clan membership automatically.**\n"
                    "Please manually check if the candidate is already in a family clan.\n\n"
                    "Run `/recruit bidding` after manual verification."
                )

        # Send recruitment lead ping with dynamic message
        await bot_instance.rest.create_message(
            channel=thread_id,
            content=notification_content,
            role_mentions=True
        )

        print(f"[SummaryGenerator] Sent candidate summary and recruitment lead ping to thread {thread_id}")
        return True
        
    except Exception as e:
        print(f"[SummaryGenerator] Error sending summary: {e}")
        import traceback
        traceback.print_exc()
        return False