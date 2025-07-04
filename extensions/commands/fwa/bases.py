import uuid
import hikari
import lightbulb

from extensions.components import register_action
from utils.mongo import MongoClient
from extensions.factories.fwa_bases import get_fwa_base_object
from utils.emoji import emojis

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
    name="fwa",
    description="All FWA-related commands",
)


@group.register()
class Bases(
    lightbulb.SlashCommand,
    name="bases",
    description="Select and display an FWA base Town Hall level",
):
    user = lightbulb.user(
        "discord-user",
        "Which user to show this for",
    )
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)

        action_id = str(uuid.uuid4())
        components = [
            Container(
                accent_color=BLUE_ACCENT,
                components=[
                    Text(content="## Select FWA Base Town Hall Level"),
                    Text(
                        content=(
                            "Use the dropdown menu below to assign the appropriate "
                            "Town Hall level for the recruit."
                        )
                    ),
                    ActionRow(
                        components=[
                            TextSelectMenu(
                                max_values=1,
                                custom_id=f"th_select:{action_id}_{self.user.id}",
                                placeholder="Select a Base...",
                                options=[
                                    SelectOption(
                                        emoji=emojis.TH17.partial_emoji,
                                        label="TH17",
                                        value="th17"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH16.partial_emoji,
                                        label="TH16",
                                        value="th16"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH15.partial_emoji,
                                        label="TH15",
                                        value="th15"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH14.partial_emoji,
                                        label="TH14",
                                        value="th14"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH13.partial_emoji,
                                        label="TH13",
                                        value="th13"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH12.partial_emoji,
                                        label="TH12",
                                        value="th12"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH11.partial_emoji,
                                        label="TH11",
                                        value="th11"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH10.partial_emoji,
                                        label="TH10",
                                        value="th10"
                                    ),
                                    SelectOption(
                                        emoji=emojis.TH9.partial_emoji,
                                        label="TH9",
                                        value="th9"
                                    ),
                                ],
                            ),
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Blue_Footer.png")]),
                    Text(
                        content=(
                            f"_Requested by "
                            f"{ctx.member.display_name if ctx.member else ctx.user.username}_"
                        )
                    ),
                ],
            )
        ]

        await ctx.respond(components=components, ephemeral=True)

@register_action("th_select" ,no_return=True)
@lightbulb.di.with_di
async def th_select(
    action_id: str,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):

    ctx: lightbulb.components.MenuContext = kwargs["ctx"]
    bracket, user_id = action_id.rsplit("_", 1)
    user_id = int(user_id)
    user = await bot.rest.fetch_member(ctx.guild_id, user_id)

    choice = ctx.interaction.values[0]
    fwa = await get_fwa_base_object(mongo)
    th_number = choice.lstrip('th')

    base_link = getattr(fwa.fwa_base_links, choice)
    components = [
        Text(content=f"{user.mention}"),
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content=f"## Town Hall {th_number}"),
                Media(
                    items=[
                        MediaItem(media=FWA_WAR_BASE[choice]),
                    ]
                ),
                ActionRow(
                    components=[
                        LinkButton(
                            url=base_link,
                            label="Click Me!",
                        )
                    ]
                ),
            ]
        ),
        Container(
            accent_color=BLUE_ACCENT,
            components=[
                Text(content="### FWA Base"),
                Text(content=(
                    "In order to proceed further, we request that you switch your active war base to the link provided above.\n\n"
                    "Once you have made the switch, please send us a screenshot like below to confirm the update.\n"
                )),
                Media(
                    items=[
                        MediaItem(media=FWA_ACTIVE_WAR_BASE[choice]),
                    ]
                ),
                Text(content=f"_Requested by {ctx.user.display_name}_")
            ]
        )
    ]
    await bot.rest.create_message(
        components=components,
        channel=ctx.channel_id
    )

loader.command(group)
