# extensions/events/message/ticket_automation/utils/constants.py
"""
Constants for ticket automation system.
"""

from utils.emoji import emojis

# Role and Channel IDs
RECRUITMENT_STAFF_ROLE = 999140213953671188
LOG_CHANNEL_ID = 1345589195695194113

# Timing Constants (in seconds)
REMINDER_DELETE_TIMEOUT = 15  # Seconds before auto-deleting reminder messages
REMINDER_TIMEOUT = 30  # Seconds before allowing another reminder to be sent
TIMEZONE_CONFIRMATION_TIMEOUT = 60  # Seconds to wait for Friend Time bot confirmation

# Friend Time Bot Configuration
FRIEND_TIME_BOT_ID = 481439443015942166
FRIEND_TIME_SET_COMMAND_ID = 924862149292085268

# Age Bracket Responses
AGE_RESPONSES = {
    "16_under": {
        "title": "🎉 **16 & Under Registered!**",
        "content": (
            "Got it! You're bringing that youthful energy!\n\n"
            "We'll find you a family-friendly clan that's the perfect fit for you.\n\n"
        ),
        "gif": "https://c.tenor.com/oxxT2JPSQccAAAAC/tenor.gif"
    },
    "17_25": {
        "title": "🎮 **17–25 Confirmed**",
        "content": (
            "Understood! You're in prime gaming years!\n\n"
            "Time to conquer the Clash world! 🏆\n\n"
        ),
        "gif": "https://c.tenor.com/twdtlMLE8UIAAAAC/tenor.gif"
    },
    "over_25": {
        "title": "🏅 **Age Locked In**",
        "content": (
            "Awesome! Experience meets strategy!\n\n"
            "Welcome to the veteran league of Clashers! 💪\n\n"
        ),
        "gif": "https://c.tenor.com/m6o-4dKGdVAAAAAC/tenor.gif"
    }
}

# Questionnaire Questions
QUESTIONNAIRE_QUESTIONS = {
    "interview_selection": {
        "next": "attack_strategies"  # Start with attack strategies after selection
    },
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
        "next": "future_clan_expectations",
        "requires_done": False
    },
    "future_clan_expectations": {
        "title": "## 🏰 **What Are You Looking For?**",
        "content": (
            "Tell us what you're hoping to find in your next clan!\n\n"
            "{red_arrow} **War frequency preferences**\n"
            "{blank}{white_arrow} _e.g. Daily wars, 2-3 times a week, CWL only_\n\n"
            "{red_arrow} **Social atmosphere**\n"
            "{blank}{white_arrow} _e.g. Competitive, casual, chatty, quiet focus_\n\n"
            "{red_arrow} **Goals & priorities**\n"
            "{blank}{white_arrow} _e.g. Push trophies, max clan games, learn strategies_\n\n"
            "*Share as much detail as you'd like - it helps us find your perfect match!*"
        ),
        "next": "discord_basic_skills",
        "requires_done": False
    },
    "discord_basic_skills": {
        "title": "## 🎯 **Quick Discord Skills Check**",
        "content": (
            "Let's make sure you're comfortable with Discord basics!\n\n"
            "**Please complete these two simple tasks:**\n\n"
            "{red_arrow} **React to this message** with any emoji\n"
            "{red_arrow} **Mention the bot** by typing @ and selecting the bot\n\n"
            "*These skills help you stay connected with your clan!*\n\n"
            "-# To continue, type **done**"
        ),
        "next": "age_bracket",
        "requires_done": True
    },
    "age_bracket": {
        "title": "## ⏳ **What's Your Age Bracket?**",
        "content": "**What age bracket do you fall into?**\n\n",
        "next": "timezone",  # Will proceed to timezone after selection
        "is_button_question": True
    },
    "timezone": {
        "title": "## 🌐 **Set Your Time Zone**",
        "content": "To help us match you with the right clan and events, let's set your timezone.\n\n",
        "next": "completion",
        "is_friend_time": True
    },
    "completion": {
        "title": "## ✅ **Questionnaire Complete!**",
        "content": (
            "🎉 **Congratulations!** You've completed the recruitment questionnaire!\n\n"
            "**What happens next:**\n"
            "• Our recruitment team will review your responses\n"
            "• We'll match you with clans that fit your preferences\n"
            "• A recruiter will reach out with clan recommendations\n\n"
            "*Thank you for taking the time to share about yourself!*"
        ),
        "next": None,
        "is_completion": True
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
        "next": "completion",
        "requires_done": False
    }
}