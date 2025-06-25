# Import the libraries
import os
import hikari
import lightbulb
from dotenv import load_dotenv
from utils.mongo import MongoClient
import coc

from utils.startup import load_cogs
load_dotenv()

# Create a GatewayBot instance
bot = hikari.GatewayBot(os.getenv("DISCORD_TOKEN"))


client = lightbulb.client_from_app(bot)

mongo_client = MongoClient(uri=os.getenv("MONGODB_URI"))

clash_client = coc.Client(
    base_url='https://proxy.clashk.ing/v1',
    key_count=10,
    load_game_data=coc.LoadGameData(default=False),
    raw_attribute=True,
)

registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
registry.register_value(MongoClient, mongo_client)
registry.register_value(coc.Client, clash_client)


@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    # Load any extensions
    all_extensions = ["extensions.components"] + load_cogs(disallowed={"example"})
    await client.load_extensions(*all_extensions)
    await client.start()
    await clash_client.login_with_tokens("")


bot.run()