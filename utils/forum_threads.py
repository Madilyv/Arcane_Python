"""
Utility functions for working with Discord forum channels in hikari.
"""

import hikari
from typing import List, Optional


async def fetch_forum_threads(
    bot: hikari.GatewayBot, 
    forum_channel_id: int,
    include_archived: bool = True
) -> List[hikari.GuildThreadChannel]:
    """
    Fetch all threads (posts) from a Discord forum channel.
    
    This is the correct way to fetch forum threads in hikari. Forum threads are 
    actually channels with the forum as their parent_id.
    
    Args:
        bot: The hikari bot instance
        forum_channel_id: The ID of the forum channel (e.g., 1378034781144744019)
        include_archived: Whether to include archived threads (default: True)
        
    Returns:
        List of thread channels in the forum
        
    Example:
        ```python
        forum_id = 1378034781144744019
        threads = await fetch_forum_threads(bot, forum_id)
        print(f"Found {len(threads)} threads in the forum")
        
        for thread in threads:
            print(f"Thread: {thread.name} (ID: {thread.id})")
        ```
    """
    threads = []
    thread_ids = set()  # Track IDs to avoid duplicates
    
    # Get the forum channel to find the guild ID
    forum_channel = await bot.rest.fetch_channel(forum_channel_id)
    guild_id = forum_channel.guild_id
    
    # Method 1: Fetch all guild channels and filter for threads in this forum
    # This is the most reliable method for getting all forum threads
    all_channels = await bot.rest.fetch_guild_channels(guild_id)
    
    for channel in all_channels:
        # Check if this is a thread that belongs to our forum
        if (hasattr(channel, 'parent_id') and 
            channel.parent_id == forum_channel_id and
            channel.type in (hikari.ChannelType.GUILD_PUBLIC_THREAD, 
                           hikari.ChannelType.GUILD_PRIVATE_THREAD,
                           hikari.ChannelType.GUILD_NEWS_THREAD)):
            threads.append(channel)
            thread_ids.add(channel.id)
    
    # Method 2: Include archived threads if requested
    if include_archived:
        try:
            # Fetch public archived threads
            archived_threads = await bot.rest.fetch_public_archived_threads(forum_channel_id)
            for thread in archived_threads:
                if thread.id not in thread_ids:
                    threads.append(thread)
                    thread_ids.add(thread.id)
        except Exception:
            # Might fail due to permissions or no archived threads
            pass
        
        try:
            # Try to fetch private archived threads (requires specific permissions)
            private_archived = await bot.rest.fetch_private_archived_threads(forum_channel_id)
            for thread in private_archived:
                if thread.id not in thread_ids:
                    threads.append(thread)
                    thread_ids.add(thread.id)
        except Exception:
            # Often fails due to permissions
            pass
    
    return threads


async def fetch_active_forum_threads(
    bot: hikari.GatewayBot, 
    forum_channel_id: int
) -> List[hikari.GuildThreadChannel]:
    """
    Fetch only active (non-archived) threads from a forum channel.
    
    Args:
        bot: The hikari bot instance
        forum_channel_id: The ID of the forum channel
        
    Returns:
        List of active thread channels in the forum
    """
    # Get the forum channel to find the guild ID
    forum_channel = await bot.rest.fetch_channel(forum_channel_id)
    guild_id = forum_channel.guild_id
    
    # Fetch all guild channels
    all_channels = await bot.rest.fetch_guild_channels(guild_id)
    
    # Filter for non-archived threads in this forum
    active_threads = []
    for channel in all_channels:
        if (hasattr(channel, 'parent_id') and 
            channel.parent_id == forum_channel_id and
            channel.type in (hikari.ChannelType.GUILD_PUBLIC_THREAD, 
                           hikari.ChannelType.GUILD_PRIVATE_THREAD,
                           hikari.ChannelType.GUILD_NEWS_THREAD)):
            # Check if thread is not archived
            if not getattr(channel, 'is_archived', False):
                active_threads.append(channel)
    
    return active_threads


async def get_forum_thread_by_name(
    bot: hikari.GatewayBot,
    forum_channel_id: int,
    thread_name: str,
    case_sensitive: bool = False
) -> Optional[hikari.GuildThreadChannel]:
    """
    Find a specific thread in a forum by name.
    
    Args:
        bot: The hikari bot instance
        forum_channel_id: The ID of the forum channel
        thread_name: The name of the thread to find
        case_sensitive: Whether to do case-sensitive matching (default: False)
        
    Returns:
        The thread channel if found, None otherwise
    """
    threads = await fetch_forum_threads(bot, forum_channel_id)
    
    for thread in threads:
        if case_sensitive:
            if thread.name == thread_name:
                return thread
        else:
            if thread.name.lower() == thread_name.lower():
                return thread
    
    return None


# Example usage for your specific case
async def example_usage(bot: hikari.GatewayBot):
    """Example of how to use these functions."""
    FORUM_CHANNEL_ID = 1378034781144744019
    
    # Get all threads
    all_threads = await fetch_forum_threads(bot, FORUM_CHANNEL_ID)
    print(f"Total threads in forum: {len(all_threads)}")
    
    # Get only active threads
    active_threads = await fetch_active_forum_threads(bot, FORUM_CHANNEL_ID)
    print(f"Active threads: {len(active_threads)}")
    
    # Find a specific thread
    specific_thread = await get_forum_thread_by_name(bot, FORUM_CHANNEL_ID, "General Discussion")
    if specific_thread:
        print(f"Found thread: {specific_thread.name} (ID: {specific_thread.id})")
    
    # Print details of all threads
    for thread in all_threads:
        archived_status = "Archived" if getattr(thread, 'is_archived', False) else "Active"
        print(f"- {thread.name} (ID: {thread.id}) - {archived_status}")