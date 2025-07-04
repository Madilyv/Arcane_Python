import lightbulb


from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    ThumbnailComponentBuilder as Thumbnail,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    LinkButtonBuilder as LinkButton
)

from utils.constants import RED_ACCENT
from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.classes import FWA
from utils.emoji import emojis

async def get_fwa_base_object(mongo):
    fwa_data = await mongo.fwa.find().to_list(length=1)
    if fwa_data:
        return FWA(data=fwa_data[0])
    return None