import hikari
import lightbulb
import coc
import pymongo

from extensions.factories import dashboard_page
from extensions.autocomplete import clans, th_attribute, clan_types
from utils.mongo import MongoClient
from utils.classes import Clan

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
    ModalActionRowBuilder as ModalActionRow
)
from utils.constants import RED_ACCENT

loader = lightbulb.Loader()
group = lightbulb.Group(
    name="clan",
    description="Clan Management Dashboard",
    default_member_permissions=hikari.Permissions.MANAGE_GUILD
)

@group.register()
class RecruitQuestions(
    lightbulb.SlashCommand,
    name="dashboard",
    description="Send the Clan Management Dashboard"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.defer(ephemeral=False)
        components = await dashboard_page()
        await ctx.respond(components=components, ephemeral=True)





loader.command(group)