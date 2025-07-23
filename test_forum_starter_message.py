"""
Test script to demonstrate fetching forum thread starter messages with images.

This script shows the correct way to fetch the initial/starter message
from a Discord forum thread, which contains the original post with any images.
"""

import hikari
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def fetch_forum_thread_starter_message(bot: hikari.GatewayBot, thread_id: int):
    """
    Fetch the starter message of a forum thread.
    
    In Discord forums, the thread ID is the same as the starter message ID.
    This is a key feature of Discord's API design.
    
    Args:
        bot: The hikari bot instance
        thread_id: The ID of the forum thread
        
    Returns:
        The starter message object or None if not found
    """
    try:
        # Method 1: Direct fetch using thread ID as message ID
        print(f"Fetching starter message for thread {thread_id}...")
        starter_message = await bot.rest.fetch_message(thread_id, thread_id)
        
        print(f"✓ Found starter message:")
        print(f"  Author: {starter_message.author}")
        print(f"  Created: {starter_message.created_at}")
        print(f"  Content: {starter_message.content[:100]}..." if starter_message.content else "  Content: (No text content)")
        
        if starter_message.attachments:
            print(f"  Attachments ({len(starter_message.attachments)}):")
            for att in starter_message.attachments:
                print(f"    - {att.filename} ({att.size} bytes)")
                print(f"      URL: {att.url}")
        else:
            print("  No attachments")
            
        return starter_message
        
    except Exception as e:
        print(f"✗ Failed to fetch starter message directly: {e}")
        
        # Method 2: Fallback - fetch all messages and get the oldest
        try:
            print("  Trying fallback method...")
            messages = await bot.rest.fetch_messages(thread_id)
            
            if messages:
                # Get the oldest message (starter message)
                starter_message = min(messages, key=lambda m: m.created_at)
                
                print(f"✓ Found starter message using fallback:")
                print(f"  Author: {starter_message.author}")
                print(f"  Created: {starter_message.created_at}")
                
                if starter_message.attachments:
                    print(f"  Attachments ({len(starter_message.attachments)}):")
                    for att in starter_message.attachments:
                        print(f"    - {att.filename} ({att.size} bytes)")
                else:
                    print("  No attachments")
                    
                return starter_message
            else:
                print("✗ No messages found in thread")
                return None
                
        except Exception as fallback_error:
            print(f"✗ Fallback also failed: {fallback_error}")
            return None


async def main():
    """Main function to test forum thread starter message fetching."""
    
    # Initialize bot
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN not found in environment variables")
        return
        
    bot = hikari.GatewayBot(token=token)
    
    # Example forum thread IDs to test
    # Replace these with actual thread IDs from your Discord server
    test_thread_ids = [
        # Add your test thread IDs here
        # 1234567890123456789,
    ]
    
    if not test_thread_ids:
        print("Please add some forum thread IDs to test in the test_thread_ids list")
        return
    
    async with bot:
        for thread_id in test_thread_ids:
            print(f"\n{'='*50}")
            await fetch_forum_thread_starter_message(bot, thread_id)
            print('='*50)


if __name__ == "__main__":
    asyncio.run(main())