import hikari
import aiohttp
from hikari.emojis import Emoji

async def steal_from_guild(
    *,
    app: hikari.GatewayBot,
    target_guild_id: int,
    source_emoji: Emoji,
    new_name: str
) -> hikari.Emoji:
    # 1) fetch the full emoji object for URL & animated flag
    full = await app.rest.fetch_emoji(source_emoji.id)

    # 2) download the bytes
    async with aiohttp.ClientSession() as session:
        resp = await session.get(str(full.url))
        resp.raise_for_status()
        data = await resp.read()

    # 3) create it in this guild
    return await app.rest.create_custom_emoji(
        guild=target_guild_id,
        name=new_name,
        image=data,
        roles=[]
    )
