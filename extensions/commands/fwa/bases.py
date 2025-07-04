import uuid
import hikari
import lightbulb

from utils.mongo import MongoClient
from extensions.factories.fwa_bases import get_fwa_base_object
from utils.constants import BLUE_ACCENT
from utils.emoji import emojis

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
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
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)

        fwa_obj = await get_fwa_base_object(mongo)

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
                                custom_id=f"th_select:{action_id}",
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

loader.command(group)
