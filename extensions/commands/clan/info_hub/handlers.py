# extensions/commands/clan/info_hub/handlers.py

import hikari
import lightbulb
import coc
from typing import List, Optional
from datetime import datetime

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    ContainerComponentBuilder as Container,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    LinkButtonBuilder as LinkButton,
    SectionComponentBuilder as Section,
    ThumbnailComponentBuilder as Thumbnail,
)

from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.constants import RED_ACCENT, GOLD_ACCENT, BLUE_ACCENT, GREEN_ACCENT, MAGENTA_ACCENT
from .helpers import get_clans_by_type, format_th_requirement, get_league_emoji

# League order for sorting
LEAGUE_ORDER = [
    "Champion League I", "Champion League II", "Champion League III",
    "Master League I", "Master League II", "Master League III",
    "Crystal League I", "Crystal League II", "Crystal League III",
    "Gold League I", "Gold League II", "Gold League III",
    "Silver League I", "Silver League II", "Silver League III",
    "Bronze League I", "Bronze League II", "Bronze League III",
    "Unranked"
]

BANNERS = {
    "Competitive": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752233879/server_banners/main_clans.png",
    "Casual": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752233879/server_banners/feeder_clans.png",
    "Zen": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752234005/server_banners/zen_clans.png",
    "FWA": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752233879/server_banners/fwa_clans.png",
    "Trial": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752233879/server_banners/trial_clans.png"
}

async def build_clan_list_components(
        ctx: lightbulb.components.MenuContext,
        clan_type: str,
        accent_color: hikari.Color,
        mongo: MongoClient,
        coc_client: coc.Client,
        bot: hikari.GatewayBot
) -> List:
    """Build components for displaying clans of a specific type"""

    # Get clans by type
    clans = await get_clans_by_type(mongo, clan_type)

    # Fetch API data for all clans
    clan_api_data = {}
    for clan in clans:
        try:
            api_clan = await coc_client.get_clan(tag=clan.tag)
            clan_api_data[clan.tag] = api_clan
        except:
            clan_api_data[clan.tag] = None

    # Sort clans by league
    def get_league_rank(clan: Clan) -> int:
        api_clan = clan_api_data.get(clan.tag)
        if not api_clan or not hasattr(api_clan, 'war_league'):
            return len(LEAGUE_ORDER) - 1  # Put unranked at the end

        league_name = api_clan.war_league.name
        try:
            return LEAGUE_ORDER.index(league_name)
        except ValueError:
            return len(LEAGUE_ORDER) - 1

    sorted_clans = sorted(clans, key=get_league_rank)

    # Build components
    components = []

    # Get the banner URL for this clan type
    banner_url = BANNERS.get(clan_type, BANNERS["Competitive"])

    components.append(
        Container(
            accent_color=accent_color,
            components=[
                Media(items=[MediaItem(media=banner_url)]),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
            ]
        )
    )

    # Clan list
    clan_components = []

    for clan in sorted_clans:
        api_clan = clan_api_data.get(clan.tag)

        # Format clan info
        clan_name = f"{clan.emoji} **{clan.name}**" if clan.emoji else f"**{clan.name}**"

        # TH requirement
        th_req = format_th_requirement(clan.th_requirements, clan.th_attribute)

        # League info
        if api_clan and hasattr(api_clan, 'war_league'):
            league_name = api_clan.war_league.name
            league_emoji = get_league_emoji(league_name)
            league_info = f"{league_emoji} {league_name}"
        else:
            league_info = "🏆 Unranked"

        # Build clan entry
        clan_text = f"{clan_name}\n{th_req} • {league_info}"

        # Add More Info link if thread_id exists
        if clan.thread_id:
            clan_text += f" • [More Info](https://discord.com/channels/{ctx.guild_id}/{clan.thread_id})"

        clan_components.append(Text(content=clan_text))

    # Add clans to container
    if clan_components:
        components.append(
            Container(
                accent_color=accent_color,
                components=[
                    Text(content=f"## {clan_type} Clans"),
                    Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                    *clan_components,
                    Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        )
    else:
        components.append(
            Container(
                accent_color=accent_color,
                components=[
                    Text(content=f"## {clan_type} Clans"),
                    Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                    Text(content=f"No {clan_type} clans found."),
                    Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        )

    return components


# Handler for Competitive/Main clans
@register_action("show_competitive", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def show_competitive_clans(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Show competitive/main clans"""
    components = await build_clan_list_components(
        ctx, "Competitive", RED_ACCENT, mongo, coc_client, bot
    )
    await ctx.respond(components=components, ephemeral=True)


# Handler for Casual/Feeder clans
@register_action("show_casual", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def show_casual_clans(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Show casual/feeder clans"""
    components = await build_clan_list_components(
        ctx, "Casual", GOLD_ACCENT, mongo, coc_client, bot
    )
    await ctx.respond(components=components, ephemeral=True)


# Handler for Zen clans
@register_action("show_zen", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def show_zen_clans(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Show Zen clans"""
    components = await build_clan_list_components(
        ctx, "Zen", GREEN_ACCENT, mongo, coc_client, bot
    )
    await ctx.respond(components=components, ephemeral=True)


# Handler for FWA clans
@register_action("show_fwa", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def show_fwa_clans(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Show FWA clans"""
    components = await build_clan_list_components(
        ctx, "FWA", BLUE_ACCENT, mongo, coc_client, bot
    )
    await ctx.respond(components=components, ephemeral=True)


# Handler for Trial clans
@register_action("show_trial", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def show_trial_clans(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    """Show trial clans"""
    # Get clans with status "Trial"
    clans = await mongo.clans.find({"status": "Trial"}).to_list(length=None)
    clans = [Clan(data=data) for data in clans]

    # Fetch API data
    clan_api_data = {}
    for clan in clans:
        try:
            api_clan = await coc_client.get_clan(tag=clan.tag)
            clan_api_data[clan.tag] = api_clan
        except:
            clan_api_data[clan.tag] = None

    # Sort by league
    def get_league_rank(clan: Clan) -> int:
        api_clan = clan_api_data.get(clan.tag)
        if not api_clan or not hasattr(api_clan, 'war_league'):
            return len(LEAGUE_ORDER) - 1

        league_name = api_clan.war_league.name
        try:
            return LEAGUE_ORDER.index(league_name)
        except ValueError:
            return len(LEAGUE_ORDER) - 1

    sorted_clans = sorted(clans, key=get_league_rank)

    # Build components
    # Get the banner URL for trial clans
    banner_url = BANNERS["Trial"]

    components = [
        Container(
            accent_color=MAGENTA_ACCENT,
            components=[
                Media(items=[MediaItem(media=banner_url)]),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                Text(content="## Clans on Trial"),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
            ]
        )
    ]

    if sorted_clans:
        clan_components = []
        for clan in sorted_clans:
            api_clan = clan_api_data.get(clan.tag)

            clan_name = f"{clan.emoji} **{clan.name}**" if clan.emoji else f"**{clan.name}**"
            th_req = format_th_requirement(clan.th_requirements, clan.th_attribute)

            if api_clan and hasattr(api_clan, 'war_league'):
                league_name = api_clan.war_league.name
                league_emoji = get_league_emoji(league_name)
                league_info = f"{league_emoji} {league_name}"
            else:
                league_info = "🏆 Unranked"

            clan_text = f"{clan_name}\n{th_req} • {league_info}"

            if clan.thread_id:
                clan_text += f" • [More Info](https://discord.com/channels/{ctx.guild_id}/{clan.thread_id})"

            clan_components.append(Text(content=clan_text))

        components.append(
            Container(
                accent_color=MAGENTA_ACCENT,
                components=[
                    *clan_components,
                    Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        )
    else:
        components.append(
            Container(
                accent_color=MAGENTA_ACCENT,
                components=[
                    Text(content="No clans are currently on trial."),
                    Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        )

    await ctx.respond(components=components, ephemeral=True)


# Handler for back button
@register_action("back_to_clan_info", ephemeral=False, no_return=True)
async def back_to_clan_info(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    """Return to main clan info menu"""
    # Edit the existing message instead of creating a new one
    # Recreate the original menu
    banner_url = "https://res.cloudinary.com/dxmtzuomk/image/upload/v1752230328/server_banners/Our-Clans.png"

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Media(items=[MediaItem(media=banner_url)]),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                Text(content=(
                    "Kings Alliance aims to provide a top tier and personalized clashing "
                    "experience. We offer a variety of clans to suit your needs, whether "
                    "you're a top-tier eSports player looking to prove your skills and "
                    "climb the leaderboards or just want to relax, farm and have fun. "
                    "Look no further than Kings and join one of our clans below."
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),

                # Main Clans Button
                Text(content=(
                    f"💎 **Main**\n"
                    "Our Main Clans host King's most competitive players. A "
                    "combination of trophy pushing giveaways and h2h wars provide for "
                    "a competitive experience."
                )),

                # Feeder Clans Button
                Text(content=(
                    f"🏆 **Feeder**\n"
                    "Main Clans full? Try one of our Feeder Clans. King's feeder clans "
                    "encapsulate the same attitude of our Main Clan system whilst you "
                    "wait."
                )),

                # Zen Button
                Text(content=(
                    f"🧘 **Zen**\n"
                    "Originally created by Arcane, Zen War Clans offer a laid-back, "
                    "stress-free environment where players can learn competitive attack "
                    "strategies without criticism: members participate in h2h wars "
                    "while farming, staying active without pressure from hero upgrades. "
                    "Active participation is required with at least one war attack; "
                    "second attacks are encouraged but not mandatory."
                )),

                # FWA Button
                Text(content=(
                    f"🌾 **FWA**\n"
                    "King's FWA Clans, part of the Farm War Alliance, offer a unique "
                    "clashing experience. Focused on strategic farming and no-hero "
                    "wars, these clans help you grow your base. Once you're upgraded "
                    "here, join one of our main clans to unleash your competitive side."
                )),

                # Clans on Trial Button
                Text(content=(
                    f"⚖️ **Clans on Trial**\n"
                    "As part of King's goal to provide a top tier clashing experience, new "
                    "clans are trialed before entering our ranks permanently. If one of "
                    "these clans catches your attention, join!"
                )),

                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "To check out the details of our clans, please press the buttons attached to "
                    "this embed. More info on Zen and FWA is available below in the buttons."
                )),

                # Action buttons
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id="show_competitive:",
                        label="Main",
                        emoji="💎"
                    ),
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id="show_casual:",
                        label="Feeder",
                        emoji="🏆"
                    ),
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id="show_zen:",
                        label="Zen",
                        emoji="🧘"
                    ),
                ]),
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id="show_fwa:",
                        label="FWA",
                        emoji="🌾"
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id="show_trial:",
                        label="Clans on Trial",
                        emoji="⚖️"
                    ),
                ]),
            ],
        )
    ]

    await ctx.interaction.edit_initial_response(components=components)