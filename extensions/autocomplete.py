from utils.mongo import MongoClient
import lightbulb
from utils.classes import Clan

@lightbulb.di.with_di
async def clan_types(
        ctx: lightbulb.AutocompleteContext[str],
        mongo: MongoClient
) -> None:
    query = ctx.focused.value or ""
    distinct = (await mongo.clans.distinct("type")) + ["Demo", "Stuff"]
    await ctx.respond([d for d in distinct if query.lower() in d.lower()])

@lightbulb.di.with_di
async def th_attribute(
        ctx: lightbulb.AutocompleteContext[str],
        mongo: MongoClient
) -> None:
    query = ctx.focused.value or ""
    distinct = (await mongo.clans.distinct("th_attribute")) + ["Demo", "Stuff"]
    await ctx.respond([d for d in distinct if query.lower() in d.lower()])


@lightbulb.di.with_di
async def clans(
        ctx: lightbulb.AutocompleteContext[str],
        mongo: MongoClient
) -> None:
    query = ctx.focused.value or ""
    clans = await mongo.clans.find().to_list(length=None)

    clans = [Clan(data=data) for data in clans]
    await ctx.respond([f"{c.name} | {c.tag}" for c in clans if query.lower() in c.name.lower()])

