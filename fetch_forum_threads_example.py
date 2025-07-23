"""
Example of how to fetch all threads from a Discord forum channel using hikari.

Forum threads in Discord are actually channels themselves with the forum as their parent_id.
They won't show up in fetch_active_threads() unless they've had recent activity.
"""

import hikari
import asyncio


async def fetch_all_forum_threads(bot: hikari.GatewayBot, forum_channel_id: int) -> list[hikari.GuildThreadChannel]:
    """
    Fetch all threads (posts) from a Discord forum channel.
    
    Args:
        bot: The hikari bot instance
        forum_channel_id: The ID of the forum channel
        
    Returns:
        List of thread channels in the forum
    """
    threads = []
    
    # First, get the forum channel to find the guild ID
    forum_channel = await bot.rest.fetch_channel(forum_channel_id)
    guild_id = forum_channel.guild_id
    
    print(f"Fetching threads for forum {forum_channel_id} in guild {guild_id}")
    
    # Method 1: Fetch all guild channels and filter
    # This is the most reliable method but requires fetching all channels
    all_channels = await bot.rest.fetch_guild_channels(guild_id)
    
    for channel in all_channels:
        # Check if this is a thread and belongs to our forum
        if (hasattr(channel, 'parent_id') and 
            channel.parent_id == forum_channel_id and
            channel.type in (hikari.ChannelType.GUILD_PUBLIC_THREAD, 
                           hikari.ChannelType.GUILD_PRIVATE_THREAD,
                           hikari.ChannelType.GUILD_NEWS_THREAD)):
            threads.append(channel)
            print(f"Found thread: {channel.name} (ID: {channel.id}, type: {channel.type})")
    
    # Method 2: Also check active threads (for recently active threads)
    # This catches threads that might have recent activity
    try:
        active_threads = await bot.rest.fetch_active_threads(guild_id)
        for thread in active_threads:
            if thread.parent_id == forum_channel_id and thread.id not in [t.id for t in threads]:
                threads.append(thread)
                print(f"Found active thread: {thread.name} (ID: {thread.id})")
    except Exception as e:
        print(f"Error fetching active threads: {e}")
    
    # Method 3: Check archived threads
    # Forum threads can be archived but still accessible
    try:
        # Fetch public archived threads
        archived_threads = await bot.rest.fetch_public_archived_threads(forum_channel_id)
        for thread in archived_threads:
            if thread.id not in [t.id for t in threads]:
                threads.append(thread)
                print(f"Found archived thread: {thread.name} (ID: {thread.id})")
    except Exception as e:
        print(f"Error fetching archived threads: {e}")
    
    # Method 4: Try private archived threads if bot has permissions
    try:
        private_archived = await bot.rest.fetch_private_archived_threads(forum_channel_id)
        for thread in private_archived:
            if thread.id not in [t.id for t in threads]:
                threads.append(thread)
                print(f"Found private archived thread: {thread.name} (ID: {thread.id})")
    except Exception as e:
        # This often fails due to permissions
        pass
    
    print(f"\nTotal threads found: {len(threads)}")
    return threads


async def get_forum_thread_details(bot: hikari.GatewayBot, thread: hikari.GuildThreadChannel):
    """
    Get details about a forum thread including the first message.
    
    Args:
        bot: The hikari bot instance
        thread: The thread channel
        
    Returns:
        Dictionary with thread details
    """
    details = {
        "name": thread.name,
        "id": thread.id,
        "created_at": thread.created_at,
        "member_count": getattr(thread, "member_count", None),
        "message_count": getattr(thread, "message_count", None),
        "is_archived": getattr(thread, "is_archived", False),
        "archive_timestamp": getattr(thread, "archive_timestamp", None),
        "first_message": None
    }
    
    # Try to get the starter message (thread ID = starter message ID in Discord forums)
    try:
        # In Discord forums, the thread ID is the same as the starter message ID
        starter_message = await bot.rest.fetch_message(thread.id, thread.id)
        details["first_message"] = {
            "content": starter_message.content,
            "author": str(starter_message.author),
            "created_at": starter_message.created_at,
            "has_attachments": bool(starter_message.attachments),
            "attachments": [
                {
                    "filename": att.filename,
                    "url": att.url,
                    "size": att.size
                } for att in starter_message.attachments
            ] if starter_message.attachments else []
        }
    except Exception as e:
        print(f"Error fetching starter message for thread {thread.id}: {e}")
        # Fallback: try to get the oldest message
        try:
            messages = await bot.rest.fetch_messages(thread.id)
            if messages:
                # Get the oldest message (starter message)
                starter_message = min(messages, key=lambda m: m.created_at)
                details["first_message"] = {
                    "content": starter_message.content,
                    "author": str(starter_message.author),
                    "created_at": starter_message.created_at,
                    "has_attachments": bool(starter_message.attachments),
                    "attachments": [
                        {
                            "filename": att.filename,
                            "url": att.url,
                            "size": att.size
                        } for att in starter_message.attachments
                    ] if starter_message.attachments else []
                }
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
    
    return details


# Example usage
async def main():
    # You would use your actual bot instance here
    bot = hikari.GatewayBot(token="YOUR_TOKEN")
    
    # The forum channel ID you provided
    FORUM_CHANNEL_ID = 1378034781144744019
    
    # Fetch all threads
    threads = await fetch_all_forum_threads(bot, FORUM_CHANNEL_ID)
    
    # Get details for each thread
    for thread in threads[:5]:  # First 5 threads as example
        details = await get_forum_thread_details(bot, thread)
        print(f"\nThread: {details['name']}")
        print(f"  Created: {details['created_at']}")
        print(f"  Archived: {details['is_archived']}")
        if details['first_message']:
            print(f"  First message by: {details['first_message']['author']}")


# Alternative: Simple function for your specific use case
async def fetch_forum_threads_simple(bot: hikari.GatewayBot, forum_channel_id: int) -> list[hikari.GuildThreadChannel]:
    """
    Simplified version - just get all threads from a forum channel.
    """
    # Get forum channel and guild ID
    forum_channel = await bot.rest.fetch_channel(forum_channel_id)
    guild_id = forum_channel.guild_id
    
    # Fetch all guild channels
    all_channels = await bot.rest.fetch_guild_channels(guild_id)
    
    # Filter for threads that belong to this forum
    forum_threads = [
        channel for channel in all_channels
        if (hasattr(channel, 'parent_id') and 
            channel.parent_id == forum_channel_id and
            channel.type in (hikari.ChannelType.GUILD_PUBLIC_THREAD, 
                           hikari.ChannelType.GUILD_PRIVATE_THREAD,
                           hikari.ChannelType.GUILD_NEWS_THREAD))
    ]
    
    # Also check archived threads
    try:
        archived = await bot.rest.fetch_public_archived_threads(forum_channel_id)
        for thread in archived:
            if thread.id not in [t.id for t in forum_threads]:
                forum_threads.append(thread)
    except:
        pass
    
    return forum_threads


if __name__ == "__main__":
    # This would be run with your bot
    asyncio.run(main())