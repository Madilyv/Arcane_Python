import os
import hikari
import lightbulb

loader = lightbulb.Loader()

ALLOWED_USER_ID = 505227988229554179

@loader.listener(hikari.MessageCreateEvent)
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if event.is_bot or event.is_webhook:
        return

    # MINE! NOT YOURS!! MINE!!!
    if event.author_id != ALLOWED_USER_ID:
        return
    content = (event.content or "").strip()
    if content == "!test":
        await event.app.rest.create_message(
            channel=event.channel_id,
            content="Hello, this is a test response!"
        )
