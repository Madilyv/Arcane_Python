import hikari
import lightbulb
from hikari.emojis import Emoji
from extensions.factories.emoji import steal_from_guild

loader = lightbulb.Loader()

@loader.command
class StealEmoji(
    lightbulb.SlashCommand,
    name="steal",
    description="Steal a custom emoji from another guild into this server",
):
    emoji = lightbulb.string(
        "emoji",
        "The custom emoji to steal (e.g. <:some_name:1234567890>)",
    )
    new_name = lightbulb.string(
        "new_name",
        "What to call the new emoji in this server",
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        if ctx.guild_id is None:
            return await ctx.respond(
                "❌ This command must be used in a server.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )

        # parse the raw input into a Hikari Emoji
        source: Emoji = hikari.emojis.Emoji.parse(self.emoji)
        created_name = self.new_name

        try:
            created = await steal_from_guild(
                app=ctx.bot,                        # ← use ctx.bot here
                target_guild_id=ctx.guild_id,
                source_emoji=source,
                new_name=created_name,
            )
        except Exception as e:
            return await ctx.respond(f"❌ Failed to steal emoji: {e}", flags=hikari.MessageFlag.EPHEMERAL)

        await ctx.respond(f"✅ Stole `:{created.name}:` (ID {created.id}) successfully!")
