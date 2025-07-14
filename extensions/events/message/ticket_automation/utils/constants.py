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
            "{blank}{white_arrow} _e.g. Competitive, casual, chatty, quiet_\n\n"
            "{red_arrow} **Play style**\n"
            "{blank}{white_arrow} _e.g. Trophy pushing, farming, war-focused_\n\n"
            "{red_arrow} **Special interests**\n"
            "{blank}{white_arrow} _e.g. Base building, FC practice, clan games_\n\n"
            "{red_arrow} **Anything else we should know?**\n"
            "{blank}{white_arrow} _e.g. Time zone preferences, language, activity level_\n\n"
            "*The more details you share, the better we can match you!*"
        ),
        "next": "discord_basic_skills",
        "requires_done": False
    },
    "discord_basic_skills": {
        "title": "## 🎮 **Discord Basic Skills Check**",
        "content": (
            "Let's make sure you know the Discord basics!\n\n"
            "{red_arrow} **Step 1:** React to this message with any emoji\n"
            "{white_arrow} _Click the smiley face below to add a reaction_\n\n"
            "{red_arrow} **Step 2:** Reply and mention the bot\n"
            "{white_arrow} _Type a message with @Arcane Bot (that's me!)_\n\n"
            "*This ensures you can interact properly in your new clan!*"
        ),
        "footer": "React to this message and mention the bot to continue!",
        "next": "age_bracket"
    },
    "age_bracket": {
        "title": "## ⏳ **What's Your Age Bracket?**",
        "content": "**What age bracket do you fall into?**\n\n",
        "next": "timezone",
        "is_button_question": True
    },
    "timezone": {
        "title": "## 🌍 **Set Your Timezone**",
        "content": (
            "Let's set your timezone so clan leaders know when you're active!\n\n"
            "{red_arrow} **Click the button below** to open Friend Time\n"
            "{red_arrow} **Select your timezone** from the dropdown\n"
            "{red_arrow} **Wait for confirmation** from Friend Time bot\n\n"
            "*This helps with war timing and coordinating attacks!*"
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
        "footer": "You've completed the questionnaire! A recruiter will be with you shortly.",
        "next": None,
        "is_final": True
    }
}

# Age Bracket Responses (moved back here from age_bracket.py)
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