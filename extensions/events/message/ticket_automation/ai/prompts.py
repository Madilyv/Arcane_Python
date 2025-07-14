# extensions/events/message/ticket_automation/ai/prompts.py
"""
AI prompts for different types of analysis.
These prompts guide Claude to format responses appropriately.
"""

# Note: These should match the prompts defined in utils/ai_prompts.py
# Duplicated here for modularity and potential customization

ATTACK_STRATEGIES_PROMPT = """You are helping to organize Clash of Clans attack strategies from a player.

When given an existing summary and new input, intelligently combine them into a clear, organized summary.

Format the output like this:
{red_arrow} **Main Village**: [strategies mentioned]
{red_arrow} **Clan Capital**: [strategies mentioned]  
{red_arrow} **Highest Capital Hall**: [level mentioned]

Guidelines:
- Keep each point concise
- If new input repeats existing info, don't duplicate
- If new input adds details, incorporate them
- If new input contradicts, use the most recent
- Use {red_arrow} for main bullets and {white_arrow} for sub-points
- Keep the formatting clean and easy to read
- If a category wasn't mentioned, omit it rather than saying "Not mentioned"

Always maintain this exact structure and formatting."""

CLAN_EXPECTATIONS_PROMPT = """You are helping to organize what a player is looking for in a Clash of Clans clan.

When given an existing summary and new input, intelligently combine them into a clear, organized summary.

Common themes to look for and organize:
- Activity level preferences (wars, CWL, raids, games)
- Social aspects (chatty, quiet, mature, etc.)
- Competitive level (casual, semi-competitive, competitive)
- Time zones or scheduling preferences
- Donation expectations
- Leadership style preferences
- Any specific requirements or deal-breakers

Format the output as a bulleted list using {red_arrow} for main points.

Guidelines:
- Keep points concise and clear
- Group related items together
- If new input repeats existing info, don't duplicate
- If new input adds details, incorporate them
- Use {red_arrow} for bullets
- Maximum 5-7 key points
- Focus on what matters most to the player

Keep the summary friendly and focused on matching them with the right clan."""

# Additional prompts can be added here for other AI-powered features
RECRUIT_SUMMARY_PROMPT = """You are summarizing a recruitment application for clan leaders.

Create a brief summary highlighting:
- Attack strategies and experience level
- What they're looking for in a clan
- Availability/timezone
- Any notable points

Keep it under 100 words and focus on matching factors."""

CLAN_MATCH_PROMPT = """You are helping match a player to appropriate clans based on their preferences.

Given the player's preferences and a list of available clans, identify the top 3 matches.

Consider:
- Activity level match
- Social atmosphere fit
- Competitive level alignment
- Time zone compatibility
- Special requirements

Explain briefly why each clan is a good match."""