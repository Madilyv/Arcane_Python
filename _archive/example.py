import hikari
import lightbulb

from extensions.factories import remove_ban_page
from extensions.autocomplete import banned_players

loader = lightbulb.Loader()
group = lightbulb.Group(
    name="ban",
    description="command-ban-description",
    default_member_permissions=hikari.Permissions.MANAGE_GUILD
)

@group.register()
class BanRemove(
    lightbulb.SlashCommand,
    name="remove",
    description="command-ban-remove-description"
):
    player = lightbulb.string(
        "options-player",
        "options-player-description",
        autocomplete=banned_players
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        components = await remove_ban_page(player_tag=self.player)
        await ctx.respond(components=components)


loader.command(group)




#Components V2
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