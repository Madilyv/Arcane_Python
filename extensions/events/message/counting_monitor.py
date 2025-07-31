# extensions/events/message/counting_monitor.py
"""
Counting channel monitor event handler.
"""

import hikari
import lightbulb
import asyncio
import random
from typing import Optional
from utils.mongo import MongoClient
from utils import bot_data

# Global instances
mongo_client: Optional[MongoClient] = None
bot_instance: Optional[hikari.GatewayBot] = None
loader = lightbulb.Loader()

# Fun facts for milestone numbers
FUN_FACTS = {
    69: "Nice! 😎",
    100: "🎉 Century mark! Keep counting!",
    420: "Blaze it! 🔥",
    500: "Half a thousand! You're doing great! 🌟",
    666: "Spooky number! 👻",
    777: "Lucky sevens! 🎰",
    1000: "🎊 ONE THOUSAND! What an achievement!",
    1234: "Sequential! 1-2-3-4! 🔢",
    1337: "L33T! You're elite now! 💻",
    2000: "Two thousand! The future is here! 🚀",
    3000: "Three thousand! You're unstoppable! 💪",
    5000: "FIVE THOUSAND! Legendary counting! 👑",
    8888: "Quadruple eights! 8️⃣8️⃣8️⃣8️⃣ So satisfying!",
    9000: "IT'S OVER 9000!!! 💥",
    9999: "One away from 10k! The tension! 😬",
    10000: "🎆 TEN THOUSAND! You've reached counting greatness! 🏆",
    11111: "All ones! 1️⃣1️⃣1️⃣1️⃣1️⃣",
    12345: "Perfect sequence! 1-2-3-4-5! 🎯",
    15000: "Fifteen thousand! Halfway to 30k! 🌈",
    20000: "TWENTY THOUSAND! Double digits! 🎊",
    22222: "All twos! 2️⃣2️⃣2️⃣2️⃣2️⃣",
    25000: "Quarter of 100k! You're amazing! 🌟",
    30000: "THIRTY THOUSAND! Incredible dedication! 💎",
    33333: "All threes! 3️⃣3️⃣3️⃣3️⃣3️⃣",
    44444: "All fours! 4️⃣4️⃣4️⃣4️⃣4️⃣",
    50000: "FIFTY THOUSAND! Half a century of thousands! 🏅",
    55555: "All fives! 5️⃣5️⃣5️⃣5️⃣5️⃣",
    66666: "All sixes! 6️⃣6️⃣6️⃣6️⃣6️⃣",
    69420: "The ultimate meme number! Nice and blazing! 😎🔥",
    77777: "All sevens! 7️⃣7️⃣7️⃣7️⃣7️⃣ JACKPOT!",
    88888: "All eights! 8️⃣8️⃣8️⃣8️⃣8️⃣",
    99999: "All nines! 9️⃣9️⃣9️⃣9️⃣9️⃣",
    100000: "💯 ONE HUNDRED THOUSAND! LEGENDARY STATUS ACHIEVED! 👑🎆🏆"
}

# Random encouragements
ENCOURAGEMENTS = [
    "Keep it up! 🌟",
    "Nice counting! 👍",
    "You're on fire! 🔥",
    "Smooth! 😎",
    "Perfect! ✨",
    "Excellent! 🎯",
    "Way to go! 🚀",
    "Counting pro! 💪",
]

def _initialize_from_bot_data():
    """Initialize using bot_data if available."""
    global mongo_client, bot_instance
    
    if "mongo" in bot_data.data:
        mongo_client = bot_data.data["mongo"]
    if "bot" in bot_data.data:
        bot_instance = bot_data.data["bot"]

@loader.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent):
    """Initialize on bot startup."""
    _initialize_from_bot_data()
    print("[Counting Monitor] Initialized")

@loader.listener(hikari.GuildMessageCreateEvent)
async def on_counting_message(event: hikari.GuildMessageCreateEvent):
    """Monitor messages in the counting channel."""
    
    # Initialize if not already done
    if not mongo_client or not bot_instance:
        _initialize_from_bot_data()
    
    if not mongo_client or not bot_instance:
        return
    
    # Check if it's the counting channel
    if str(event.channel_id) != "1024845669820796928":
        return
    
    # Ignore bot messages
    if event.is_bot:
        return
    
    # Get counting channel data
    channel_data = await mongo_client.counting_channels.find_one({"channel_id": str(event.channel_id)})
    
    if not channel_data or not channel_data.get("enabled", True):
        return
    
    current_number = channel_data.get("current_number", 0)
    expected_number = current_number + 1
    last_counter_id = channel_data.get("last_counter_id")
    
    # Check if the message is a valid number
    try:
        user_number = int(event.content.strip())
    except ValueError:
        # Not a number - delete and warn
        try:
            await event.message.delete()
            # Send ephemeral-like follow-up that auto-deletes
            warning = await event.get_channel().send(
                f"<@{event.author_id}> HEY this is a counting channel! what do you think you're doing. 🤨",
                user_mentions=[event.author_id]
            )
            # Delete warning after 5 seconds
            await asyncio.sleep(5)
            await warning.delete()
        except:
            pass
        return
    
    # Check if the same user is trying to count again
    if last_counter_id and last_counter_id == str(event.author_id):
        # Delete their message
        try:
            await event.message.delete()
            # Send warning
            warning = await event.get_channel().send(
                f"<@{event.author_id}> WOAH WOAH WOAH, don't be greedy! Other people want to learn to count as well! 🛑",
                user_mentions=[event.author_id]
            )
            # Delete warning after 7 seconds
            await asyncio.sleep(7)
            await warning.delete()
        except:
            pass
        return
    
    # Check if it's the correct number
    if user_number == expected_number:
        # Correct number!
        # Update the database
        await mongo_client.counting_channels.update_one(
            {"channel_id": str(event.channel_id)},
            {"$set": {
                "current_number": user_number,
                "last_counter_id": str(event.author_id)
            }}
        )
        
        # Add reactions for milestones or randomly
        try:
            # Check for milestone
            if user_number in FUN_FACTS:
                await event.message.add_reaction("🎉")
                # Send milestone message
                milestone_msg = await event.get_channel().send(FUN_FACTS[user_number])
                # Delete after 10 seconds
                await asyncio.sleep(10)
                await milestone_msg.delete()
            # Random encouragement (5% chance)
            elif random.random() < 0.05:
                await event.message.add_reaction("✅")
                encouragement = random.choice(ENCOURAGEMENTS)
                enc_msg = await event.get_channel().send(encouragement)
                await asyncio.sleep(5)
                await enc_msg.delete()
        except:
            pass
            
    else:
        # Wrong number - delete and notify
        try:
            await event.message.delete()
            
            # Determine the error message
            if user_number < expected_number:
                error_msg = f"<@{event.author_id}> Oops! We already passed {user_number}. The next number is **{expected_number}**! 📉"
            else:
                error_msg = f"<@{event.author_id}> Whoa, slow down! You skipped some numbers. The next number is **{expected_number}**! 📈"
            
            # Send error message that auto-deletes
            error = await event.get_channel().send(
                error_msg,
                user_mentions=[event.author_id]
            )
            # Delete error after 7 seconds
            await asyncio.sleep(7)
            await error.delete()
        except:
            pass

@loader.listener(hikari.GuildMessageDeleteEvent)
async def on_counting_message_delete(event: hikari.GuildMessageDeleteEvent):
    """Handle when a counting message is deleted."""
    
    # Check if it's the counting channel
    if str(event.channel_id) != "1024845669820796928":
        return
    
    # We could implement logic here to handle deleted count messages
    # For now, we'll just let it be - the count continues from where it was