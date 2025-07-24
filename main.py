import warnings
# Ignore deprecation warnings from coc.py library about datetime.utcnow()
warnings.filterwarnings("ignore", category=DeprecationWarning, module="coc.http")
# Also ignore from any coc submodules
warnings.filterwarnings("ignore", category=DeprecationWarning, module="coc.*")
# Ignore specific datetime.utcnow() deprecation warning
warnings.filterwarnings("ignore", message="datetime.datetime.utcnow\\(\\) is deprecated")

import logging
# Suppress py.warnings logger to hide deprecation warnings in terminal
logging.getLogger("py.warnings").setLevel(logging.ERROR)

import os
import hikari
import lightbulb
from dotenv import load_dotenv
from utils.mongo import MongoClient
import coc
from utils.startup import load_cogs
from utils.cloudinary_client import CloudinaryClient
from extensions.autocomplete import preload_autocomplete_cache
from utils.session_cleanup import start_cleanup_task
from extensions.events.message import dm_screenshot_upload
from utils import bot_data

load_dotenv()

# Create a GatewayBot instance with intents
bot = hikari.GatewayBot(
    token=os.getenv("DISCORD_TOKEN"),
    intents=(
        hikari.Intents.GUILD_MESSAGES
        | hikari.Intents.MESSAGE_CONTENT
        | hikari.Intents.GUILDS
        | hikari.Intents.GUILD_MEMBERS
        | hikari.Intents.GUILD_MODERATION
        | hikari.Intents.GUILD_MESSAGE_REACTIONS
    ),
)

client = lightbulb.client_from_app(bot)

mongo_client = MongoClient(uri=os.getenv("MONGODB_URI"))
clash_client = coc.Client(
    base_url='https://proxy.clashk.ing/v1',
    key_count=10,
    load_game_data=coc.LoadGameData(default=False),
    raw_attribute=True,
)

cloudinary_client = CloudinaryClient()

bot_data.data["mongo"] = mongo_client
bot_data.data["cloudinary_client"] = cloudinary_client
bot_data.data["bot"] = bot
bot_data.data["coc_client"] = clash_client

registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
registry.register_value(MongoClient, mongo_client)
registry.register_value(coc.Client, clash_client)
registry.register_value(CloudinaryClient, cloudinary_client)
registry.register_value(hikari.GatewayBot, bot)

@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    """Bot starting event"""
    all_extensions = [
        "extensions.components",
        "extensions.commands.clan.list",
        "extensions.commands.fwa.bases",
        "extensions.context_menus.get_message_id",
        "extensions.context_menus.get_user_id",
        "extensions.events.message.message_events",
        "extensions.events.message.task_manager",
        "extensions.events.channel.ticket_channel_monitor",
        "extensions.events.channel.ticket_close_monitor",
        "extensions.events.message.ticket_screenshot",
        "extensions.commands.clan.dashboard.dashboard",
        "extensions.commands.recruit.questions",
        "extensions.tasks.band_monitor",
        "extensions.tasks.clanpoints_autoboard",
        "extensions.tasks.reddit.clan_post_monitor",
        "extensions.tasks.reddit.th15_search_monitor",
        "extensions.tasks.reddit.th16_search_monitor",
        "extensions.tasks.reddit.th17_search_monitor",
        "extensions.tasks.expire_new_recruits",
        "extensions.tasks.recruit_monitor",
        "extensions.tasks.clan_info_updater",
        "extensions.tasks.bidding_recovery",
        "extensions.commands.moderation",
        "extensions.commands.fwa.upload_images",
        "extensions.commands.fwa.war_plans",
        "extensions.commands.clan.report",
        "extensions.commands.clan.info_hub",
        "extensions.events.message.ticket_account_collection",
         "extensions.commands.help",
        "extensions.commands.utilities",
    ] + load_cogs(disallowed={"example"})

    await client.load_extensions(*all_extensions)
    await client.start()
    await clash_client.login_with_tokens("")

    dm_screenshot_upload.load(bot)
    start_cleanup_task()
    # print("Bot started with DM screenshot listener and cleanup task")

@bot.listen(hikari.StoppingEvent)
async def on_stopping(_: hikari.StoppingEvent) -> None:
    """Bot stopping event"""
    dm_screenshot_upload.unload(bot)
    # print("Bot stopped, event listeners unloaded")
    # Properly close the coc.py client to avoid unclosed session warnings
    await clash_client.close()

bot.run()