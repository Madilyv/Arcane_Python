import uuid
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from extensions.factories.fwa_bases import get_fwa_base_object
from utils.emoji import emojis
from utils.classes import Clan
from utils.constants import RED_ACCENT, GOLD_ACCENT,BLUE_ACCENT,GREEN_ACCENT,FWA_WAR_BASE,FWA_ACTIVE_WAR_BASE

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

loader = lightbulb.Loader()

group = lightbulb.Group(
    name="clan",
    description="All Clan-related commands",
)

@group.register()
class ListCommand(
    lightbulb.SlashCommand,
    name="list",
    description="Just says hello",
):
    @lightbulb.invoke
    async def invoke(
            self,
            ctx: lightbulb.Context,
            mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        clan_data = await mongo.clans.find().to_list(length=None)
        clans = [Clan(data=data) for data in clan_data]
        options = [
            SelectOption(label=c.name, value=c.tag, description=c.tag, emoji=c.partial_emoji)
            for c in clans
        ]
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[

                    Text(content=
                         "## **Pick Your Clan**\n"
                         "Use the dropdown below to select your clan.\n"
                         "If your clan isn’t listed, notify Ruggie."

                         ),
                    ActionRow(
                        components=[
                            TextSelectMenu(
                                custom_id=f"clan_select_menu:",
                                placeholder="Select a clan",
                                max_values=1,
                                options=options,
                            )
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ],
            )
        ]
        await ctx.respond(
            content=None,
            components=components,
            ephemeral=True
        )

@register_action("clan_select_menu", ephemeral=True)
@lightbulb.di.with_di
async def on_clan_chosen(
    ctx: lightbulb.components.MenuContext,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    # 1) pull the selected tag
    tag = ctx.interaction.values[0]

    # 2) fetch that clan
    raw = await mongo.clans.find_one({"tag": tag})
    if not raw:
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content="⚠️ Sorry, I couldn’t find that clan in the database.")
                ]
            )
        ]
        return components

    clan = Clan(data=raw)

    # 3) build your components list
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                # — Title & Subtitle —
                Text(content=f"## **{clan.name}**"),
                Text(content="**Clan Info**"),
                Separator(divider=True),

                # # — Fields —
                # Section(
                #     components=[
                #         Text(content=f"{emojis.white_arrow_right}**Clan Level:** {clan.level}"),
                #     ]
                # ),
                # Section(
                #     components=[
                #         Text(
                #             content=f"{emojis.white_arrow_right}**CWL Rank:** {clan.war_league.name if hasattr(clan, 'war_league') else clan.cwl_rank}"),
                #     ]
                # ),
                # Section(
                #     components=[
                #         Text(
                #             content=f"{emojis.white_arrow_right}**Capital Peak:** {clan.capital_building.level if hasattr(clan, 'capital_building') else clan.capital_peak}"),
                #     ]
                # ),
                # Section(
                #     components=[
                #         Text(content=f"{emojis.white_arrow_right}**Clan Tag:** `{clan.tag}`"),
                #     ]
                # ),
                #
                # # — Thumbnail (little badge up top) —
                # Thumbnail(media=clan.badge_url or clan.logo),

                # # — Big Logo Art —
                # Media(items=[MediaItem(media=clan.logo)]),
                #
                # Separator(divider=True),
                #
                # # — Footer text —
                # Text(content=f"Command ran by {ctx.member.mention}"),
                #
                # # — “Open In-Game” Link Button —
                # ActionRow(
                #     components=[
                #         LinkButton(
                #             label="Open In-Game",
                #             url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={clan.tag}"
                #         )
                #     ]
                # ),
            ]
        )
    ]

    # 4) return it
    return components

loader.command(group)