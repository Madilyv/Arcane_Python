import lightbulb

import hikari
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
    MediaGalleryItemBuilder as MediaItem
)
from utils.constants import RED_ACCENT
from utils.emoji import emojis
from extensions.components import register_action

@register_action("primary_questions", no_return=True)
@lightbulb.di.with_di
async def primary_questions(
    user_id: int,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):

    ctx: lightbulb.components.MenuContext = kwargs.get("ctx")

    print("⮞ primary_questions args:", ctx, user_id, "kwargs:", kwargs)
    choice = ctx.interaction.values[0]
    user = await bot.rest.fetch_member(ctx.guild_id, user_id)

    if choice == "attack_strategies":
        components = [
            Text(content=user.mention),
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        "## Let's Talk Strategies\n"
                        f"{emojis.red_arrow_right} What strategies do you use for your main village?\n"
                        f"{emojis.blank}{emojis.white_arrow_right} (e.g., Hybrid, Queen Charge w/ Hydra, Lalo, etc.)\n\n"
                        f"{emojis.red_arrow_right} What strategies do you use for Clan Capital, and what level are you familiar with?\n"
                        f"{emojis.blank}{emojis.white_arrow_right} (e.g., Super Miners w/ Freeze, familiar with Capital Hall 8+.)\n\n"
                        "*Please provide detailed answers to help us better understand your experience and playstyle.*"
                    )),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                    ]),
                    Text(content=(
                        f"-# Command ran by {ctx.user.display_name}"
                    ))
                ]
            )
        ]
        await bot.rest.create_message(
            components=components,
            channel=ctx.channel_id
        )


async def recruit_questions_page(
    action_id: str,
    user_id: int,
    **kwargs
):
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=(
                    "Streamline your recruitment process with this all-in-one toolkit. "
                    "Each section is designed to help you efficiently guide candidates into the Arcane Alliance family.\n\n"
                    f"{emojis.red_arrow_right} Primary Questions: Select and send tailored questions to candidates.\n"
                    f"{emojis.red_arrow_right} Explanations: Provide clear and concise info about FWA, Zen, and other Alliance essentials.\n"
                    f"{emojis.red_arrow_right} FWA Questions: Access primary FWA-specific questions and prompts.\n"
                    f"{emojis.red_arrow_right} Keep It Moving: Use quick and fun 'hurry up' GIFs to maintain momentum.\n\n"
                    "Stay organized, efficient, and aligned with Arcane’s recruitment standards.\n\n"
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "Other Useful Commands\n"
                    f"{emojis.red_arrow_right}  Get Clans\n"
                    "<:aa_a_w:1036081848633282691> /get clans\n"
                    f"{emojis.red_arrow_right}  Deny Recruit\n"
                    "<:aa_a_w:1036081848633282691> /get recruit-deny\n"
                    f"{emojis.red_arrow_right}  Base Weight\n"
                    "<:aa_a_w:1036081848633282691> /fwa weight\n"
                    f"{emojis.red_arrow_right}  Chocolate Clash\n"
                    "<:aa_a_w:1036081848633282691> /fwa chocolate"
                )),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            max_values=1,
                            custom_id=f"primary_questions:{action_id}",
                            placeholder="Primary Questions",
                            options=[
                                SelectOption(
                                    emoji=1387846413211402352,
                                    label="Attack Strategies",
                                    value="attack_strategies"),
                                SelectOption(
                                    emoji=1387846432316194837,
                                    label="Future Clan Expectations",
                                    value="future_clan_expectations"),
                                SelectOption(
                                    emoji=1387846461672132649,
                                    label="Discord Basic Skills",
                                    value="discord_basic_skills"),
                                SelectOption(
                                    emoji=1387846482220159168,
                                    label="Discord Basic Skills pt.2",
                                    value="discord_basic_skills2"),
                                SelectOption(
                                    emoji=1387846506589061220,
                                    label="Age Bracket & Timezone",
                                    value="age_bracket_&_timezone"),
                                SelectOption(
                                    emoji=1387846529229787246,
                                    label="Leaders Checking You Out",
                                    value="leaders_checking_you_out"),
                    ]),
                ]),
                Text(content="-# Kings Alliance - Where Legends Are Made"),
                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png")
                ]),
            ]),
        ]

    return components
