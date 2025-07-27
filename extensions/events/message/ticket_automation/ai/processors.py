# extensions/events/message/ticket_automation/ai/processors.py
"""
AI processing functions for analyzing user responses.
Uses Claude API to intelligently summarize and format responses.
"""

import os
import aiohttp
import json
from typing import Optional

from .prompts import ATTACK_STRATEGIES_PROMPT, CLAN_EXPECTATIONS_PROMPT

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Model configuration
AI_MODEL = "claude-3-haiku-20240307"
MAX_TOKENS = 1000


def analyze_attack_strategies_progress(summary: str) -> dict:
    """
    Analyze the attack strategies summary to determine progress.
    
    Args:
        summary: The formatted attack strategies summary
    
    Returns:
        Dict with progress indicators
    """
    progress = {
        "has_main_village": False,
        "has_capital": False,
        "has_ch_level": False
    }
    
    if not summary:
        return progress
    
    # Check for main village strategies
    if "**Main Village Strategies:**" in summary:
        # Look for actual strategies, not just "No input provided"
        main_section = summary.split("**Main Village Strategies:**")[1].split("**Clan Capital Strategies:**")[0]
        if "No input provided" not in main_section and "{white_arrow}" in main_section:
            # Check if there's actual content after the arrow
            lines = main_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_main_village"] = True
                    break
    
    # Check for clan capital strategies
    if "**Clan Capital Strategies:**" in summary:
        capital_section = summary.split("**Clan Capital Strategies:**")[1].split("**Familiarity with Clan Capital Levels:**")[0]
        if "No input provided" not in capital_section and "{white_arrow}" in capital_section:
            lines = capital_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_capital"] = True
                    break
    
    # Check for CH level familiarity
    if "**Familiarity with Clan Capital Levels:**" in summary:
        ch_section = summary.split("**Familiarity with Clan Capital Levels:**")[1]
        if "No input provided" not in ch_section and "{white_arrow}" in ch_section:
            lines = ch_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_ch_level"] = True
                    break
    
    return progress


def analyze_clan_expectations_progress(summary: str) -> dict:
    """
    Analyze the clan expectations summary to determine progress.
    
    Args:
        summary: The formatted clan expectations summary
    
    Returns:
        Dict with progress indicators
    """
    progress = {
        "has_expectations": False,
        "has_clan_level": False,
        "has_capital_hall": False,
        "has_cwl_league": False,
        "has_clan_style": False
    }
    
    if not summary:
        return progress
    
    # Check for expectations
    if "**Expectations:**" in summary:
        expectations_section = summary.split("**Expectations:**")[1].split("**Minimum Clan Level:**")[0]
        if "No input provided" not in expectations_section and "{white_arrow}" in expectations_section:
            lines = expectations_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_expectations"] = True
                    break
    
    # Check for minimum clan level
    if "**Minimum Clan Level:**" in summary:
        clan_level_section = summary.split("**Minimum Clan Level:**")[1].split("**Minimum Clan Capital Hall Level:**")[0]
        if "No input provided" not in clan_level_section and "{white_arrow}" in clan_level_section:
            lines = clan_level_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_clan_level"] = True
                    break
    
    # Check for capital hall level
    if "**Minimum Clan Capital Hall Level:**" in summary:
        capital_hall_section = summary.split("**Minimum Clan Capital Hall Level:**")[1].split("**CWL League Preference:**")[0]
        if "No input provided" not in capital_hall_section and "{white_arrow}" in capital_hall_section:
            lines = capital_hall_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_capital_hall"] = True
                    break
    
    # Check for CWL league preference
    if "**CWL League Preference:**" in summary:
        cwl_section = summary.split("**CWL League Preference:**")[1].split("**Clan Style Preference:**")[0]
        if "No input provided" not in cwl_section and "{white_arrow}" in cwl_section:
            lines = cwl_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_cwl_league"] = True
                    break
    
    # Check for clan style preference
    if "**Clan Style Preference:**" in summary:
        style_section = summary.split("**Clan Style Preference:**")[1]
        if "No input provided" not in style_section and "{white_arrow}" in style_section:
            lines = style_section.strip().split('\n')
            for line in lines:
                if "{white_arrow}" in line and len(line.split("{white_arrow}")[1].strip()) > 0:
                    progress["has_clan_style"] = True
                    break
    
    return progress


async def process_attack_strategies_with_ai(existing_summary: str, new_input: str) -> tuple[str, dict]:
    """
    Process attack strategies using Claude AI.

    Args:
        existing_summary: Current summary of strategies
        new_input: New user input to incorporate

    Returns:
        Tuple of (updated summary, progress dict)
    """

    if not ANTHROPIC_API_KEY:
        print("[AI] Warning: ANTHROPIC_API_KEY not set, returning raw input")
        # Simple detection for progress
        progress = {
            "has_main_village": False,
            "has_capital": False,
            "has_ch_level": False
        }
        return new_input, progress

    messages = [
        {
            "role": "user",
            "content": f"Existing summary:\n{existing_summary if existing_summary else 'None'}\n\nNew user input:\n{new_input}"
        }
    ]

    try:
        result = await _call_claude_api(messages, ATTACK_STRATEGIES_PROMPT)
        if not result:
            return existing_summary, {"has_main_village": False, "has_capital": False, "has_ch_level": False}
        
        # Analyze the result to determine progress
        progress = analyze_attack_strategies_progress(result)
        
        return result, progress
    except Exception as e:
        print(f"[AI] Error processing attack strategies: {e}")
        return existing_summary if existing_summary else new_input, {"has_main_village": False, "has_capital": False, "has_ch_level": False}


async def process_clan_expectations_with_ai(existing_summary: str, new_input: str) -> tuple[str, dict]:
    """
    Process clan expectations using Claude AI.

    Args:
        existing_summary: Current summary of expectations
        new_input: New user input to incorporate

    Returns:
        Tuple of (updated summary, progress dict)
    """

    if not ANTHROPIC_API_KEY:
        print("[AI] Warning: ANTHROPIC_API_KEY not set, returning raw input")
        # Simple detection for progress
        progress = {
            "has_expectations": False,
            "has_clan_level": False,
            "has_capital_hall": False,
            "has_cwl_league": False,
            "has_clan_style": False
        }
        return new_input, progress

    messages = [
        {
            "role": "user",
            "content": f"Existing summary:\n{existing_summary if existing_summary else 'None'}\n\nNew user input:\n{new_input}"
        }
    ]

    try:
        result = await _call_claude_api(messages, CLAN_EXPECTATIONS_PROMPT)
        if not result:
            return existing_summary, {
                "has_expectations": False,
                "has_clan_level": False,
                "has_capital_hall": False,
                "has_cwl_league": False,
                "has_clan_style": False
            }
        
        # Analyze the result to determine progress
        progress = analyze_clan_expectations_progress(result)
        
        return result, progress
    except Exception as e:
        print(f"[AI] Error processing clan expectations: {e}")
        return existing_summary if existing_summary else new_input, {
            "has_expectations": False,
            "has_clan_level": False,
            "has_capital_hall": False,
            "has_cwl_league": False,
            "has_clan_style": False
        }


async def _call_claude_api(messages: list, system_prompt: str) -> Optional[str]:
    """
    Internal function to call Claude API.

    Args:
        messages: List of message dictionaries
        system_prompt: System prompt for the AI

    Returns:
        AI response text or None on error
    """

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
        "system": system_prompt
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    error_text = await response.text()
                    print(f"[AI] API error {response.status}: {error_text}")
                    return None
    except aiohttp.ClientError as e:
        print(f"[AI] Network error calling Claude API: {e}")
        return None
    except Exception as e:
        print(f"[AI] Unexpected error calling Claude API: {e}")
        return None