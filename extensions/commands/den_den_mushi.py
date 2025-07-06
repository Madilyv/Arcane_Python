import lightbulb
import hikari

loader = lightbulb.Loader()


@loader.command
class Echo(
    lightbulb.SlashCommand,
    name="den-den-mushi",
    description="Broadcasts your message via the Den Den Mushi transponder snail.",
):
    text = lightbulb.string("text", "🐌 Whisper into the transponder snail")

    @lightbulb.invoke
    async def invoke(self,
                     ctx: lightbulb.Context,
                     bot: hikari.GatewayBot = lightbulb.di.INJECTED,
                     ) -> None:

        await ctx.defer(ephemeral=True)
        await bot.rest.create_message(
            channel=ctx.channel_id,
            content=self.text,
            user_mentions=True

        )
        await ctx.interaction.delete_initial_response()