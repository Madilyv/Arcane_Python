import uuid
import hikari
import lightbulb

from extensions.commands.recruit import recruit
from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan
from utils.constants import RED_ACCENT

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    TextDisplayComponentBuilder as Text,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)


@recruit.register()
class Welcome(
    lightbulb.SlashCommand,
    name="welcome",
    description="Send a clan's welcome message to a user",
):
    user = lightbulb.user(
        "user",
        "Which user to send the welcome message to",
    )

    @lightbulb.invoke
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        clan_data = await mongo.clans.find().to_list(length=None)
        clans = [Clan(data=d) for d in clan_data]

        options = []
        for c in clans:
            kwargs = {"label": c.name, "value": c.tag, "description": c.tag}
            if getattr(c, "partial_emoji", None):
                kwargs["emoji"] = c.partial_emoji
            options.append(SelectOption(**kwargs))

        action_id = str(uuid.uuid4())

        # Store user selection in button store for the handler
        await mongo.button_store.insert_one({
            "_id": action_id,
            "selected_user_id": self.user.id,
            "invoker_id": ctx.user.id
        })

        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        "## **Pick Your Clan**\n"
                        "Use the dropdown below to select which clan's welcome message to send.\n"
                        f"This will be sent to {self.user.mention}."
                    )),
                    ActionRow(
                        components=[
                            TextSelectMenu(
                                custom_id=f"clan_welcome_select:{action_id}",
                                placeholder="Select a clan",
                                max_values=1,
                                options=options,
                            )
                        ]
                    ),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ],
            )
        ]
        await ctx.respond(components=components, ephemeral=True)


@register_action("clan_welcome_select", no_return=True)
@lightbulb.di.with_di
async def on_clan_welcome_chosen(
    action_id: str,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]
    
    # Get stored data
    store_data = await mongo.button_store.find_one({"_id": action_id})
    if not store_data:
        await ctx.respond("Session expired. Please try again.", ephemeral=True)
        return
    
    selected_user_id = store_data["selected_user_id"]
    user = await bot.rest.fetch_member(ctx.guild_id, selected_user_id)

    tag = ctx.interaction.values[0]
    raw = await mongo.clans.find_one({"tag": tag})
    if not raw:
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[Text(content="⚠️ I couldn't find that clan in our database.")]
            )
        ]
        await ctx.interaction.edit_initial_response(components=components)
        return

    db_clan = Clan(data=raw)

    # Check if clan has recruit_welcome message
    if not db_clan.recruit_welcome:
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        f"⚠️ {db_clan.name} doesn't have a welcome message set up.\n\n"
                        "Please message Ruggie what welcome you would like displayed."
                    )),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        ]
        await ctx.interaction.edit_initial_response(components=components)
        return

    # Check if clan has chat_channel_id
    if not db_clan.chat_channel_id:
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        f"⚠️ {db_clan.name} doesn't have a chat channel configured.\n\n"
                        "Cannot send welcome message."
                    )),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        ]
        await ctx.interaction.edit_initial_response(components=components)
        return

    # Send the welcome message to the clan's chat channel
    try:
        await bot.rest.create_message(
            channel=db_clan.chat_channel_id,
            content=f"{user.mention}\n{db_clan.recruit_welcome}",
            user_mentions=[user.id],
        )

        # Update the original message to show success
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        f"✅ Welcome message sent to {user.mention} in <#{db_clan.chat_channel_id}>!\n\n"
                        f"**Clan:** {db_clan.name}"
                    )),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        ]
        await ctx.interaction.edit_initial_response(components=components)

    except Exception as e:
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        f"❌ Failed to send welcome message.\n\n"
                        f"Error: {str(e)[:100]}"
                    )),
                    Media(items=[MediaItem(media="assets/Red_Footer.png")]),
                ]
            )
        ]
        await ctx.interaction.edit_initial_response(components=components)
    finally:
        # Clean up button store
        await mongo.button_store.delete_one({"_id": action_id})