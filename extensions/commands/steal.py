import hikari
import lightbulb
import aiohttp

loader = lightbulb.Loader()

@loader.command
class StealEmoji(
    lightbulb.SlashCommand,
    name="steal",
    description="Steal a custom emoji into your bot application, deleting any old one of the same name.",
    default_member_permissions=hikari.Permissions.CREATE_GUILD_EXPRESSIONS
):
    # required argument
    emoji = lightbulb.string(
        "emoji",
        "The emoji to steal (e.g. <:some_name:1234567890>)"
    )
    # now optional
    new_name = lightbulb.string(
        "new_name",
        "What to call it in your application",
        default=None
    )

    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context,
        bot: hikari.GatewayBot
    ) -> None:
        await ctx.defer()
        try:
            source: hikari.CustomEmoji = hikari.emojis.Emoji.parse(self.emoji)
        except Exception:
            await ctx.respond("❌ Invalid emoji format—make sure it looks like `<:name:id>`.")
            return

        # download the image bytes
        emoji_bytes = await source.read()
        # if new_name is None or empty, use the original emoji's name
        emoji_name = self.new_name or source.name

        # re-upload with your bot’s application
        created = await bot.rest.create_application_emoji(
            application=bot.get_me().id,
            name=emoji_name,
            image=emoji_bytes,
        )

        await ctx.respond(
            f"✅ Stole and created `:{created.name}:` (ID {created.id}) in your application!"
        )
