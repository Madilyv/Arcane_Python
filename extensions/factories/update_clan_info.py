from logging import exception

import lightbulb
import hikari
import coc
import requests
import re

from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectMenuBuilder as SelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    ThumbnailComponentBuilder as Thumbnail,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
    ModalActionRowBuilder as ModalActionRow
)

from extensions.components import register_action
from io import BytesIO
from PIL import Image

from utils.constants import RED_ACCENT
from utils.classes import Clan
from utils.emoji import emojis
from utils.mongo import MongoClient
from extensions.factories import dashboard_page
from extensions.factories import update_clan_info_general

IMG_RE = re.compile(r"^https?://\S+\.(?:png|jpe?g|gif|webp)$", re.IGNORECASE)


@register_action("update_clan_information", group="clan_database")
@lightbulb.di.with_di
async def update_clan_information(
        ctx: lightbulb.components.MenuContext,
        **kwargs
):
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=(
                    "### Update Clan Information\n\n"
                    "Select an action below to manage clan information in our database.\n\n"
                    f"{emojis.white_arrow_right}**Edit a Clan:** Modify details of an existing clan.\n"
                    f"{emojis.white_arrow_right}**Add a Clan:** Add a new clan with all relevant information.\n"
                    f"{emojis.white_arrow_right}**Remove a Clan:** Delete a clan and all its associated information.\n"
                )),

                Section(
                    components=[
                        Text(
                            content=(
                                f"{emojis.white_arrow_right}"
                                "**Add a Clan:** Add a new clan with all relevant information."
                            )
                        )
                    ],
                    accessory=Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Add a Clan",
                        custom_id="add_clan_page:",
                    ),
                ),
                Section(
                    components=[
                        Text(
                            content=(
                                f"{emojis.white_arrow_right}"
                                "**Edit a Clan:** Modify details of an existing Clan"
                            )
                        )
                    ],
                    accessory=Button(
                        style=hikari.ButtonStyle.SUCCESS,
                        label="Edit a Clan",
                        custom_id="choose_clan_select:",
                    ),
                ),

                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png"),
                    ])
            ]
        )
    ]
    await ctx.respond(components=components, ephemeral=True)

    return await dashboard_page(ctx=ctx)



#ADD CLAN STUFF
@register_action("add_clan_page")
@lightbulb.di.with_di
async def add_clan_page(
        ctx: lightbulb.components.MenuContext,
        **kwargs
):
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=(
                    "### Add a New Clan\n\n"
                    "To add a new clan, you will need to be ready to supply all the core details of the new clan. These include:\n"
                    f"{emojis.white_arrow_right}Clan Name\n"
                    f"{emojis.white_arrow_right}Clan ID\n"
                    f"{emojis.white_arrow_right}Leadership (Leader ID & Role ID\n"
                    f"{emojis.white_arrow_right}Clan Role ID\n"
                    f"{emojis.white_arrow_right}Clan Type\n"
                    f"{emojis.white_arrow_right}Logo\n"
                    f"{emojis.white_arrow_right}TH Requirements\n"
                )),
                ActionRow(components=[
                    Button(style=hikari.ButtonStyle.SECONDARY, custom_id="add_clan:", label="Add the New Clan")
                ])
            ]
        )
    ]
    return components



@register_action("add_clan", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def add_clan(
        ctx: lightbulb.components.MenuContext,
        **kwargs
):
    tag = ModalActionRow().add_text_input(
        "clantag",
        "Clan Tag",
        placeholder="Enter a Clan Tag",
        required=True
    )
    await ctx.respond_with_modal(
        title="Add Clan",
        custom_id=f"add_clan_modal:",
        components=[tag]
    )



@register_action("add_clan_modal", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def add_clan_modal(
        ctx: lightbulb.components.ModalContext,
        coc_client: coc.Client = lightbulb.di.INJECTED,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    def get_modal_item(ctx: lightbulb.components.ModalContext, custom_id: str):
        for row in ctx.interaction.components:
            for component in row:
                if component.custom_id == custom_id:
                    return component.value

    clan_tag = get_modal_item(ctx, "clantag")
    if not clan_tag:
        return await ctx.respond("⚠️ You must enter a clan tag!", ephemeral=True)

    clan = await coc_client.get_clan(tag=clan_tag)
    await mongo.clans.insert_one({
        "announcement_id": 0,
        "chat_channel_id": 0,
        "emoji": "",
        "leader_id": 0,
        "leader_role_id": 0,
        "leadership_channel_id": 0,
        "logo": "",
        "name": clan.name,
        "profile": "",
        "role_id": 0,
        "rules_channel_id": 0,
        "status": "",
        "tag": clan.tag,
        "th_attribute": "",
        "th_requirements": 0,
        "thread_id": 0,
        "type": ""
    })
    await ctx.respond(
        content=f"✅ Got it! Clan Tag is `{clan.tag}`. Name is {clan.name}",
        ephemeral=True
    )


#EDIT CLAN STUFF
@register_action("choose_clan_select", ephemeral=True)
@lightbulb.di.with_di
async def choose_clan_select(
        ctx: lightbulb.components.MenuContext,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    clans = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=data) for data in clans]
    options = [
        SelectOption(label=c.name, value=c.tag, description=c.tag)
        for c in clans
    ]

    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[

                Text(content="✏️ **Which clan would you like to edit?**"),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            custom_id=f"clan_edit_menu:",
                            placeholder="Select a clan to edit…",
                            max_values=1,
                            options=options,
                        )
                    ]
                ),
                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
            ],
        )
    ]
    return components


@register_action("clan_edit_menu", ephemeral=True)
@lightbulb.di.with_di
async def clan_edit_menu(
        ctx: lightbulb.components.MenuContext,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    tag = kwargs.get("tag") or ctx.interaction.values[0]

    raw = await mongo.clans.find_one({"tag": tag})
    db_clan = Clan(data=raw)


    guild_id = ctx.interaction.guild_id
    channel_link = f"https://discord.com/channels/{guild_id}/"

    components = [Container(
        accent_color=RED_ACCENT,
        components=[
            Text(content=f"## ✏️ **Editing {db_clan.name}** (`{db_clan.tag}`)"),
            Separator(divider=True, spacing=hikari.SpacingType.LARGE),

            # General Clan Info
            Text(content="\n## __🛡️ General Info__"),
            Text(
                content=(
                    f"{emojis.white_arrow_right}**Clan Type:** {db_clan.type or '⚠️ Data Missing'}\n"
                    f"{emojis.white_arrow_right}**Clan Status:** {db_clan.status or '⚠️ Data Missing'}\n"
                    f"{emojis.white_arrow_right}**Logo:** {db_clan.logo or '⚠️ Data Missing'}\n"
                    f"{emojis.white_arrow_right}**Emoji:** {db_clan.emoji or '⚠️ Data Missing'}\n"
                    f"{emojis.white_arrow_right}**TH Requirement:** {db_clan.th_requirements or '⚠️ Data Missing'}\n"
                    f"{emojis.white_arrow_right}**TH Attribute:** {db_clan.th_attribute or '⚠️ Data Missing'}"
                )
            ),

            # Clan Roles
            Separator(divider=True, spacing=hikari.SpacingType.SMALL),
            Text(content="\n## __👤 Roles__"),
            Text(content=(
                f"**Leader:** {f'<@{db_clan.leader_id}>' if db_clan.leader_id else '⚠️ Data Missing'}"
            )),

            ActionRow(
                components=[
                    SelectMenu(
                        min_values=1,
                        type=hikari.ComponentType.USER_SELECT_MENU,
                        custom_id = f"edit_clan:leader_id_{tag}",
                        placeholder="Select the leader...",
                    ),
                ]
            ),
            Text(content=(
                f"**Leader Role:** {f'<@&{db_clan.leader_role_id}>' if db_clan.leader_role_id else '⚠️ Data Missing'}"
            )),

            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.ROLE_SELECT_MENU,
                        custom_id = f"edit_clan:leader_role_id_{tag}",
                        placeholder="Select the leader role...",
                    ),
                ]
            ),
            Text(content=(
                f"**Clan Role:** {f'<@&{db_clan.role_id}>' if db_clan.role_id else '⚠️ Data Missing'}"
            )),

            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.ROLE_SELECT_MENU,
                        custom_id = f"edit_clan:role_id_{tag}",
                        placeholder="Select the clan role...",
                    ),
                ]
            ),

            # Clan Channel
            Separator(divider=True, spacing=hikari.SpacingType.SMALL),
            Text(content="\n## __💬 Channels__"),
            Text(content=(
                f"**Chat Channel:** {f'<#{db_clan.chat_channel_id}>' if db_clan.chat_channel_id else '⚠️ Data Missing'}"
            ))
            ,
            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.CHANNEL_SELECT_MENU,
                        custom_id=f"edit_clan:chat_channel_id_{tag}",
                        placeholder="Select a channel..",
                    ),
                ]
            ),
            Text(content=(
                f"**Announcement Channel:** {f'<#{db_clan.announcement_id}>' if db_clan.announcement_id else '⚠️ Data Missing'}"
            )),
            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.CHANNEL_SELECT_MENU,
                        custom_id = f"edit_clan:announcement_id_{tag}",
                        placeholder="Select a channel..",
                    ),
                ]
            ),
            Text(content=(
                f"**Rules Channel:** {f'<#{db_clan.rules_channel_id}>' if db_clan.rules_channel_id else '⚠️ Data Missing'}"
            )),
            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.CHANNEL_SELECT_MENU,
                        custom_id = f"edit_clan:rules_channel_id_{tag}",
                        placeholder="Select a channel..",
                    ),
                ]
            ),
            Text(content=(
                f"**Leadership Channel:** {f'<#{db_clan.leadership_channel_id}>' if db_clan.leadership_channel_id else '⚠️ Data Missing'}"
            )),
            ActionRow(
                components=[
                    SelectMenu(
                        type=hikari.ComponentType.CHANNEL_SELECT_MENU,
                        custom_id = f"edit_clan:leadership_channel_id_{tag}",
                        placeholder="Select a channel..",
                    ),
                ]
            ),
            Text(content=(
                f"**Clan Thread:** {f'<#{db_clan.thread_id}>' if db_clan.thread_id else '⚠️ Data Missing'}"
            )),

            # Thread is Auto Thread Create
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id=f"edit_thread:thread_id_{db_clan.tag}",
                        label="Add Clan Thread",
                    )
                ]
            ),
            Separator(divider=True, spacing=hikari.SpacingType.SMALL),
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id=f"update_logo:{db_clan.tag}",
                        label="Update Logo",
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id=f"update_emoji:{db_clan.tag}",
                        label="Update Emoji",
                    ),
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id=f"update_general_info:{db_clan.tag}",
                        label="Edit General Info",
                    ),
                ]
            ),
            Media(items=[MediaItem(media="assets/Red_Footer.png")]),
        ],
    )]
    return components


@register_action("edit_clan", ephemeral=True)
@lightbulb.di.with_di
async def on_edit_clan_field(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    field, tag = action_id.rsplit("_", 1)
    raw_val = ctx.interaction.values[0]
    selected = int(raw_val) if raw_val.isdigit() else raw_val

    await mongo.clans.update_one({"tag": tag}, {"$set": {field : selected}})

    return await clan_edit_menu(
        ctx=ctx,
        mongo=mongo,
        tag=tag
    )


@register_action("edit_thread", ephemeral=True)
@lightbulb.di.with_di
async def on_edit_thread_field(
        ctx: lightbulb.components.MenuContext,
        action_id: str,                       # e.g. "edit_thread:thread_id_LYUQG8CL"
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        mongo: MongoClient   = lightbulb.di.INJECTED,
        **kwargs
):

    field, tag = action_id.rsplit("_", 1)

    guild_id = ctx.interaction.guild_id
    PARENT_CH = 1133096989748363294

    raw = await mongo.clans.find_one({"tag": tag})

    active = await bot.rest.fetch_active_threads(guild_id)
    p_arch = await bot.rest.fetch_public_archived_threads(PARENT_CH)

    threads = [t for t in list(active) + list(p_arch) if t.parent_id == PARENT_CH and t.name == raw["name"]]

    if threads:
        thread = threads[0]
    else:
        thread = await bot.rest.create_thread(
            PARENT_CH,
            hikari.ChannelType.GUILD_PRIVATE_THREAD,
            raw["name"],
            auto_archive_duration=1440,
        )

    await mongo.clans.update_one({"tag": tag}, {"$set": {"thread_id": thread.id}})

    # 5) Rebuild the edit menu
    return await clan_edit_menu(
        ctx=ctx,
        mongo=mongo,
        tag=tag
    )


@register_action("update_logo", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_logo_button(
        ctx: lightbulb.components.MenuContext,
        action_id: str,
        **kwargs
):
    tag = action_id

    logo_input = ModalActionRow().add_text_input(
        "logo_url", "Logo Image URL",
        placeholder="https://…/logo.png",
        required=True,
    )

    await ctx.respond_with_modal(
        title=f"Update Logo & Emoji for {tag}",
        custom_id=f"update_logo_modal:{tag}",
        components=[logo_input],
    )


@register_action("update_logo_modal", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_logo_modal(
        ctx: lightbulb.components.ModalContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        **kwargs
):
    tag = action_id

    def get_val(cid: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == cid:
                    return comp.value
        return ""

    new_logo_url  = get_val("logo_url")

    if new_logo_url:
        if not IMG_RE.match(new_logo_url):
            return await ctx.respond(
                "⚠️ `logo_url` must be a direct link to a .png/.jpg/.gif/.webp image.",
                ephemeral=True
            )

    # Persist both
    await mongo.clans.update_one(
        {"tag": tag},
        {"$set": {"logo": new_logo_url}}
    )

    await ctx.interaction.create_initial_response(hikari.ResponseType.DEFERRED_MESSAGE_UPDATE)
    new_components = await clan_edit_menu(ctx, action_id=tag, mongo=mongo, tag=tag)
    await ctx.interaction.edit_initial_response(components=new_components)


@register_action("update_emoji", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_emoji_button(
    ctx: lightbulb.components.MenuContext,
    action_id: str,   # this is your clan tag
    **kwargs
):
    tag = action_id

    # only one input now
    emoji_input = ModalActionRow().add_text_input(
        "emoji_url", "New Clan Emoji URL",
        placeholder="https://…/emoji.png",
        required=True,
    )

    await ctx.respond_with_modal(
        title=f"Update Emoji for {tag}",
        custom_id=f"update_emoji_modal:{tag}",
        components=[emoji_input],
    )

@register_action("update_emoji_modal", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_emoji_modal(
    ctx: lightbulb.components.ModalContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    tag = action_id
    def get_val(cid: str) -> str:
        for row in ctx.interaction.components:
            for comp in row:
                if comp.custom_id == cid:
                    return comp.value
        return ""
    new_emoji_url = get_val("emoji_url")

    emoji = ""
    print(tag)
    if new_emoji_url:
        def resize_and_compress_image(image_content, max_size=(128, 128), max_kb=256):
            image = Image.open(BytesIO(image_content))
            print("Hi I am here")
            image.thumbnail(max_size)

            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            buffer_size = buffer.tell() / 1024

            if buffer_size > max_kb:
                buffer = BytesIO()
                image.save(buffer, format='PNG', optimize=True, quality=85)

            return buffer.getvalue()

        image_resp = requests.get(new_emoji_url)
        image_resp.raise_for_status()
        desired_resized_data = resize_and_compress_image(image_resp.content)

        application = await bot.rest.fetch_my_user()
        emoji = await bot.rest.create_application_emoji(
            application=application.id,
            name=f"{tag.replace('#', '')}",
            image=desired_resized_data
        )
        emoji = emoji.mention
        await mongo.clans.update_one(
            {"tag": tag},
            {"$set": {"emoji": emoji}}
        )

    new_components = await clan_edit_menu(ctx=ctx, mongo=mongo, tag=tag)
    await ctx.edit_response(components=new_components)
