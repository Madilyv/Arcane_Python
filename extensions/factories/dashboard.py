

import lightbulb
import pymongo
import hikari
import coc
from PIL import Image
from io import BytesIO
import requests

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
from lightbulb import channel
from lightbulb.components import MenuContext, ModalContext
from utils.emoji import EmojiType
from extensions.autocomplete import clan_types
from utils.constants import RED_ACCENT,CLAN_TYPES,TH_LEVELS,CLAN_STATUS,TH_ATTRIBUTE
from utils.emoji import emojis
from extensions.components import register_action
from utils.mongo import MongoClient
from utils.classes import Clan


@register_action("add_clan_page", no_return=True)
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
    await ctx.respond(components=components, ephemeral=True)

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
        custom_id=f"add_clan_modal:{ctx.interaction.id}",
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
        await ctx.respond("⚠️ You must enter a clan tag!", ephemeral=True)
        return

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

@register_action("edit_clan_menu", ephemeral=True)
@lightbulb.di.with_di
async def edit_clan_menu(
    ctx: lightbulb.components.MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    # Figure out the tag (either passed in or from the dropdown)
    # tag = kwargs.get("tag") or (ctx.interaction.values or [None])[0]
    # If the user selected from the dropdown, .values will be non‐empty:
    # if ctx.interaction.values:
    #     tag = ctx.interaction.values[0]
    # else:
    #     # button click (including “Back”): action_id is your tag
    #     tag = action_id
    # pull out any select‐menu values if they exist, otherwise fall
    # back to our action_id (button clicks and modal callbacks)
    # --- your existing logic to figure out tag ---
    values = getattr(ctx.interaction, "values", None)
    tag = kwargs.get("tag")
    print(tag)

    # 1) If no tag yet, show dropdown
    if not tag:
        clans = await mongo.clans.find().to_list(length=None)
        options = [
            SelectOption(label=c["name"], value=c["tag"], description=c["tag"])
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
                                custom_id=f"edit_clan_menu:{action_id}",
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
        #return await ctx.respond(components=components, ephemeral=True)

    raw = await mongo.clans.find_one({"tag": tag})
    if not raw:
        # the decorator wrapper will catch this and send the ephemeral error
        return await ctx.respond("❌ Couldn’t find that clan!", ephemeral=True)

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

            #Thread is Auto Thread Create
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
                        custom_id=f"update_logo:{db_clan.tag}",  # <-- note colon!
                        label="Update Clan Logo & Emoji",
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

@register_action("edit_clan_action_menu", no_return=True)
@lightbulb.di.with_di
async def on_edit_action(
        ctx: MenuContext,
        action_id: str,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    choice = ctx.interaction.values[0]
    print(choice)

##### Update Each Select Menu
@register_action("edit_clan", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def on_edit_clan_field(
    ctx: MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):

    values = getattr(ctx.interaction, "values", None)
    # If there are no values, this wasn’t a select menu—skip it
    if not values:
        return

    # 1) Persist your change
    field, tag = action_id.rsplit("_", 1)
    raw_val = ctx.interaction.values[0]
    try:
        selected = int(raw_val)
    except ValueError:
        selected = raw_val
    await mongo.clans.update_one({"tag": tag}, {"$set": {field: selected}})
    print(f"this Is the tag:{tag}")
    # 2) Bypass the decorator wrapper:
    #    call the undecorated handler to get your components back
    new_components = await edit_clan_menu.__wrapped__(
        ctx,
        action_id=tag,
        mongo=mongo,
        tag=tag
    )

    # 3) Edit the original response with that fresh list
    await ctx.interaction.edit_initial_response(components=new_components)



##### END Update Each Select Menu

################CLAN THREAD

@register_action("edit_thread", ephemeral=True, no_return=True)
@lightbulb.di.with_di
async def on_edit_thread_field(
    ctx: MenuContext,
    action_id: str,                       # e.g. "edit_thread:thread_id_LYUQG8CL"
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    mongo: MongoClient   = lightbulb.di.INJECTED,
    **kwargs
):
    print("hi")
    # 1) Parse field & tag
    full_field, tag = action_id.rsplit("_", 1)
    _, field = full_field.split(":", 1)  # field == "thread_id"

    # 2) Create or fetch the thread
    guild_id = ctx.interaction.guild_id
    PARENT_CH = 1133096989748363294

    active   = await bot.rest.fetch_active_threads(guild_id)
    p_arch   = await bot.rest.fetch_public_archived_threads(PARENT_CH)
    pr_arch  = await bot.rest.fetch_private_archived_threads(PARENT_CH)
    threads  = [t for t in active if t.parent_id == PARENT_CH] + p_arch + pr_arch

    raw      = await mongo.clans.find_one({"tag": tag})
    clan_name = raw["name"]

    for thr in threads:
        if thr.name == clan_name:
            new_id = thr.id
            break
    else:
        new_thr = await bot.rest.create_thread(
            channel=PARENT_CH,
            name=clan_name,
            auto_archive_duration=1440,
        )
        new_id = new_thr.id

    # 3) Persist the new thread_id
    await mongo.clans.update_one({"tag": tag}, {"$set": {field: new_id}})

    # 4) Confirm to user
    thread_url = f"https://discord.com/channels/{guild_id}/{PARENT_CH}/{new_id}"
    await ctx.respond(f"✅ Thread for **{clan_name}** set: {thread_url}", ephemeral=True)

    # 5) Rebuild the edit menu
    new_components = await edit_clan_menu.__wrapped__(
        ctx=ctx,
        action_id=tag,
        mongo=mongo,
        tag=tag
    )
    await ctx.interaction.edit_initial_response(components=new_components)





#################CLAN THREAD


### I NEED TO DETERMINE HOW TO GRAB THE URL AND UPLOAD TO THE DATABASE
# 1) Button‐click (opens the modal)
@register_action("update_logo", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_logo_button(
    ctx: MenuContext,     # <-- use MenuContext here
    action_id: str,       # this is your clan tag
    **kwargs
):
    tag = action_id

    emoji_input = ModalActionRow().add_text_input(
        "logo_emoji", "New Clan Emoji",
        placeholder="https://…/logo.png",
        required=True,
    )
    logo_input = ModalActionRow().add_text_input(
        "logo_url", "Logo Image URL",
        placeholder="https://…/logo.png",
        required=True,
    )

    await ctx.respond_with_modal(
        title="Update Clan Logo & Emoji",
        custom_id=f"update_logo_modal:{tag}",
        components=[emoji_input, logo_input],
    )


# 2) Modal‐submit (handles the data)
import re
IMG_RE = re.compile(r"^https?://.+\.(?:png|jpe?g|gif|webp)$", re.IGNORECASE)

@register_action("update_logo_modal", no_return=True, is_modal=True)
@lightbulb.di.with_di
async def update_logo_modal(
    ctx: ModalContext,
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
    new_emoji_url = get_val("logo_emoji")
    new_logo_url  = get_val("logo_url")

    emoji = ""
    if new_emoji_url:
        def resize_and_compress_image(image_content, max_size=(128, 128), max_kb=256):
            image = Image.open(BytesIO(image_content))

            # Resize image
            image.thumbnail(max_size)

            # Save to a bytes buffer
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            buffer_size = buffer.tell() / 1024  # Size in KB

            if buffer_size > max_kb:
                buffer = BytesIO()
                image.save(buffer, format='PNG', optimize=True, quality=85)  # Adjust quality as needed

            return buffer.getvalue()

        image_resp = requests.get(new_emoji_url)
        image_resp.raise_for_status()
        desired_resized_data = resize_and_compress_image(image_resp.content)
    
        application = await bot.rest.fetch_my_user()
        emoji = await bot.rest.create_application_emoji(
            application=application.id,
            name=f"{tag}",
            image=resize_and_compress_image(image_content=desired_resized_data)
        )
        emoji = emoji.mention

    # Persist
    await mongo.clans.update_one(
        {"tag": tag},
        {"$set": {"emoji": emoji, "logo": new_logo_url}}
    )

    # Acknowledge & refresh your edit menu
    await ctx.interaction.create_initial_response(
        hikari.ResponseType.DEFERRED_MESSAGE_UPDATE
    )
    new_components = await edit_clan_menu(ctx, action_id=tag, mongo=mongo, tag=tag)
    await ctx.interaction.edit_initial_response(components=new_components)
    await ctx.interaction.create_followup(
        content=f"✅ Clan **{tag}** updated! Emoji & logo saved.",
    )





# 1) Change the decorator to *not* use no_return=True
@register_action("update_general_info", ephemeral=True)
@lightbulb.di.with_di
async def update_general_info_panel(
    ctx: MenuContext,
    action_id: str,               # clan tag
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    tag = action_id
    raw = await mongo.clans.find_one({"tag": tag})
    if not raw:
        # you can still early‐respond on error
        await ctx.respond("❌ Clan not found!", ephemeral=True)

    db_clan = Clan(data=raw)
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"## ✏️ **Editing {db_clan.name}** (`{db_clan.tag}`)"),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                Text(content=f"{emojis.white_arrow_right}**Clan Type:** {db_clan.type or '⚠️ Missing'}\n"),
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"edit_general:type_{tag}",
                        placeholder="Select the clan type…",
                        min_values=1,
                        max_values=1,
                        options=[
                            SelectOption(label=ctype, value=ctype)
                            for ctype in CLAN_TYPES
                        ],
                    )
                ]),
                Text(content=f"{emojis.white_arrow_right}**Clan Status:** {db_clan.status or '⚠️ Missing'}\n"),
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"edit_general:status_{tag}",
                        placeholder="Select the clan status…",
                        min_values=1,
                        max_values=1,
                        options=[
                            SelectOption(label=ctype, value=ctype)
                            for ctype in CLAN_STATUS
                        ],
                    )
                ]),
                Text(content=f"{emojis.white_arrow_right}**TH Requirement:** {db_clan.th_requirements or '⚠️ Missing'}\n"),
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"edit_general:th_requirements_{tag}",
                        placeholder="Select the TH requirement…",
                        min_values=1,
                        max_values=1,
                        options=[
                            SelectOption(label=f"{lvl}", value=lvl)
                            for lvl in TH_LEVELS
                        ],
                    )
                ]),
                Text(content=f"{emojis.white_arrow_right}**TH Attribute:** {db_clan.th_attribute or '⚠️ Missing'}\n"),
                ActionRow(components=[
                    TextSelectMenu(
                        custom_id=f"edit_general:th_attribute_{tag}",
                        placeholder="Select the TH Attribute…",
                        min_values=1,
                        max_values=1,
                        options=[
                            SelectOption(label=ctype, value=ctype)
                            for ctype in TH_ATTRIBUTE
                        ],
                    )
                ]),
                Separator(divider=True, spacing=hikari.SpacingType.LARGE),
                ActionRow(components=[
                    Button(
                        style=hikari.ButtonStyle.SECONDARY,
                        custom_id=f"edit_clan_menu:{tag}",
                        label="« Back",
                    )
                ]),
                Media(items=[MediaItem(media="assets/Red_Footer.png")]),
            ],
        )
    ]
    return components





# 2️⃣ The live-update handler matches your old pattern
@register_action("edit_general", no_return=True, ephemeral=True)
@lightbulb.di.with_di
async def on_edit_general(
    ctx: MenuContext,
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    # parse out the field & tag
    field, tag = action_id.rsplit("_", 1)
    selected = ctx.interaction.values[0]

    # persist
    await mongo.clans.update_one({"tag": tag}, {"$set": {field: selected}})

    # rebuild & redraw
    new_components = await update_general_info_panel(
        ctx=ctx,
        action_id=tag,
        mongo=mongo
    )
    await ctx.interaction.edit_initial_response(components=new_components)






### NEW LOST RUGGIE 2

@register_action("clan_database", no_return=True)
@lightbulb.di.with_di
async def clan_database(
        ctx: lightbulb.components.MenuContext,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    #action_id = str(ctx.interaction.id)

    clan_data = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=data) for data in clan_data]

    clan_list = ""
    for clan in clans:
        clan_list += f"{clan.name} ({clan.tag})\n"

    if ctx.interaction.values[0] == "view_clan_list":
        #View Clan List message here
        components = [
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        "### Current Clan List\n\n"
                        f"{clan_list}"
                    )),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                        ])
                ]
            )
        ]
        await ctx.respond(components=components, ephemeral=True)


    # Update Clan Information Components
    elif ctx.interaction.values[0] == "update_clan_information":
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
                            custom_id="edit_clan_menu:",
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



# Main Clan Dashboard Management
@lightbulb.di.with_di
async def dashboard_page(
        action_id: str,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
        ctx: lightbulb.Context = lightbulb.di.INJECTED,
        mongo: MongoClient = lightbulb.di.INJECTED,
        **kwargs
):
    clan_data = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=data) for data in clan_data]
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Section(
                    accessory=Thumbnail(
                        media=bot.cache.get_guild(ctx.guild_id).make_icon_url()
                    ),
                    components=[
                        Text(content=(
                            "### Clan Management Dashboard\n"
                            "welcome to the Kings Alliance Clan Management Dashboard\n\n"
                            f"{emojis.white_arrow_right}**Clans in System:** `{len(clans)}`\n\n"
                        )),
                    ]
                ),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    "Use the dropdown menu below to:\n"
                    f"{emojis.white_arrow_right}View clan details\n"
                    f"{emojis.white_arrow_right}Track & Update Clan Points\n"
                    f"{emojis.white_arrow_right}Update Clan Information\n"
                    f"{emojis.white_arrow_right}Update FWA Data\n"
                )),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            max_values=1,
                            custom_id=f"clan_database:{action_id}",
                            placeholder="Make a Selection...",
                            options=[
                                SelectOption(
                                    label="View Clan List",
                                    description="View all clans & their IDs",
                                    value="view_clan_list"),
                                SelectOption(
                                    label="Clan Points",
                                    description="Track & Update Clan Points",
                                    value="clan_points"),
                                SelectOption(
                                    label="Update Clan Information",
                                    description="Edit or Manage Clan Details",
                                    value="update_clan_information"),
                                SelectOption(
                                    label="Manage FWA Data",
                                    description="Update FWA Links & Images",
                                    value="manage_fwa_data"),
                            ]),
                    ]),
                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png")
                    ]),
            ]
        )
    ]
    return components