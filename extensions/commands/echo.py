import lightbulb

loader = lightbulb.Loader()

@loader.command
class Echo(
    lightbulb.SlashCommand,
    name="echo",
    description="echo",
):
    text = lightbulb.string("text", "the text to repeat")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(self.text)