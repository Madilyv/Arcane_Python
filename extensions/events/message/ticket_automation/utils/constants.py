# extensions/events/message/ticket_automation/utils/constants.py
"""
Constants specific to ticket automation questionnaire.
Separated from main constants for modularity.
"""

# Role and Channel IDs
RECRUITMENT_STAFF_ROLE = 999140213953671188
LOG_CHANNEL_ID = 1345589195695194113

# Timing Configuration
REMINDER_DELETE_TIMEOUT = 15  # Seconds before auto-deleting reminder messages
REMINDER_TIMEOUT = 30  # Seconds before allowing another reminder
TIMEZONE_CONFIRMATION_TIMEOUT = 60  # Seconds to wait for Friend Time bot

# Friend Time Bot ID
FRIEND_TIME_BOT_ID = 481439443015942166

# Question Definitions
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
        "type": "ai_continuous",
        "next": "future_clan_expectations"
    },
    "future_clan_expectations": {
        "title": "## 🏰 **What are you looking for in a Future clan?**",
        "content": (
            "Tell us your ideal clan experience!\n\n"
            "{red_arrow} **Examples to consider:**\n"
            "{blank}{white_arrow} Activity level _(wars, CWL, raids, games)_\n"
            "{blank}{white_arrow} Social atmosphere _(chatty, quiet, mature)_\n"
            "{blank}{white_arrow} Competition level _(casual to hardcore)_\n"
            "{blank}{white_arrow} Special preferences _(time zones, leadership style)_\n\n"
            "*Share what matters most to you!*"
        ),
        "type": "ai_continuous",
        "next": "discord_basic_skills"
    },
    "discord_basic_skills": {
        "title": "## 🎯 **Discord Basic Skills Check**",
        "content": (
            "Let's verify you know the Discord basics!\n\n"
            "{red_arrow} **Complete these two simple tasks:**\n\n"
            "{blank}1️⃣ **React** to this message with any emoji\n"
            "{blank}2️⃣ **Reply** and mention me in your message\n\n"
            "*These skills are essential for clan communication!*"
        ),
        "type": "skill_check",
        "footer": "React to this message and mention the bot to continue!",
        "next": "discord_basic_skills_2"
    },
    "discord_basic_skills_2": {
        "title": "## 💬 **Quick Communication Check**",
        "content": (
            "One more Discord skill to verify!\n\n"
            "**Can you see and use our custom emojis?**\n\n"
            "These are special to our server:\n"
            "• Clash emojis for troops and spells\n"
            "• Rank indicators\n"
            "• Clan badges\n\n"
            "-# To continue, type `done` below"
        ),
        "type": "text_response",
        "expected_response": "done",
        "next": "age_bracket"
    },
    "age_bracket": {
        "title": "## 🎂 **Select Your Age Bracket**",
        "content": (
            "This helps us find age-appropriate clans for you.\n\n"
            "*Your selection is kept private and only used for clan matching.*"
        ),
        "type": "button_selection",
        "has_gif": True,
        "next": "timezone"
    },
    "timezone": {
        "title": "## 🌍 **What's Your Time Zone?**",
        "content": (
            "Help us coordinate clan activities at convenient times!\n\n"
            "**Please type one of these formats:**\n"
            "• Your timezone code: `EST`, `CST`, `PST`, `GMT`\n"
            "• UTC offset: `UTC-5`, `UTC+2`\n"
            "• Major city: `New York`, `London`, `Sydney`\n\n"
            "*Friend Time bot will save this for easy conversions!*"
        ),
        "type": "text_response",
        "wait_for_bot": True,
        "bot_id": FRIEND_TIME_BOT_ID,
        "next": "leaders_checking_you_out"
    },
    "leaders_checking_you_out": {
        "title": "## 👀 **Clan Leaders are Checking You Out!**",
        "content": (
            "Your application is looking great!\n\n"
            "Our clan leaders are reviewing your responses to find the perfect match.\n\n"
            "*Get ready to join an amazing community!*"
        ),
        "type": "final_message",
        "has_gif": True,
        "gif_url": "https://media1.tenor.com/m/BkGs-OUqeZ0AAAAC/well.gif",
        "next": None
    }
}