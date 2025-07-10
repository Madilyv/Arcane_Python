# events/message/test_screenshot.py
# A minimal test version to verify event listening works

import hikari


def load(bot: hikari.GatewayBot) -> None:
    bot.subscribe(hikari.GuildMessageCreateEvent, test_message_handler)
    print("[TEST] Screenshot test listener loaded")


def unload(bot: hikari.GatewayBot) -> None:
    bot.unsubscribe(hikari.GuildMessageCreateEvent, test_message_handler)
    print("[TEST] Screenshot test listener unloaded")


async def test_message_handler(event: hikari.GuildMessageCreateEvent) -> None:
    """Simple test handler"""
    # Skip bot messages
    if event.is_bot:
        return

    # Check for attachments
    if event.message.attachments:
        print(f"[TEST] Detected message with {len(event.message.attachments)} attachments")
        print(f"[TEST] From user: {event.author_id} in channel: {event.channel_id}")

        # Check for images
        for att in event.message.attachments:
            if att.media_type and att.media_type.startswith("image/"):
                print(f"[TEST] Found image: {att.filename} ({att.size} bytes)")

                # Try to respond
                try:
                    await event.message.respond("✅ I see your image!")
                except Exception as e:
                    print(f"[TEST] Error responding: {e}")