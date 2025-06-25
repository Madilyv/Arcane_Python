import hikari
import lightbulb

from utils.mongo import MongoClient
from extensions.factories import recruit_questions_page

loader = lightbulb.Loader()
group = lightbulb.Group(
    name="recruit",
    description="Recruit questions description",
    default_member_permissions=hikari.Permissions.MANAGE_GUILD
)

@group.register()
class RecruitQuestions(
    lightbulb.SlashCommand,
    name="questions",
    description="Select a new recruit to send them recruit questions"
):
    user = lightbulb.user(
        "discord_user",
        "select a new recruit",
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, mongo: MongoClient) -> None:
        await ctx.defer(ephemeral=True)
        data = {
            "_id": str(ctx.interaction.id),
            "user_id" : self.user.id
        }
        await mongo.button_store.insert_one(data)
        components = await recruit_questions_page(action_id=str(ctx.interaction.id), **data)
        await ctx.respond(components=components, ephemeral=True)


loader.command(group)