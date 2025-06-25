import lightbulb
import pymongo
import hikari
import coc
from PIL import Image
from io import BytesIO
import requests

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectMenuBuilder as SelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    ThumbnailComponentBuilder as Thumbnail,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow
)
from lightbulb import channel
from lightbulb.components import MenuContext, ModalContext
from utils.emoji import EmojiType
from extensions.autocomplete import clan_types
from utils.constants import RED_ACCENT ,CLAN_TYPES ,TH_LEVELS ,CLAN_STATUS ,TH_ATTRIBUTE
from utils.emoji import emojis
from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from extensions.factories.dashboard import dashboard_page

@register_action("view_clan_list", group="clan_database")
@lightbulb.di.with_di
async def view_clan_list(
        ctx: lightbulb.components.MenuContext,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    clan_data = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=data) for data in clan_data]

    clan_list = ""
    for clan in clans:
        clan_list += f"{clan.name} ({clan.tag})\n"

    # View Clan List message here
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=(
                    "### Current Clan List\n\n"
                    f"{clan_list}"
                )),
            ]
        )
    ]
    await ctx.respond(components=components, ephemeral=True)

    return (await dashboard_page(ctx=ctx))


