import uuid
import hikari
import lightbulb
import coc

from extensions.commands.clan   import loader, clan
from extensions.components      import register_action
from utils.mongo                import MongoClient
from utils.classes              import Clan
from utils.constants            import RED_ACCENT
from utils.emoji                import emojis

from hikari.impl import (
    MessageActionRowBuilder         as ActionRow,
    TextSelectMenuBuilder           as TextSelectMenu,
    SelectOptionBuilder             as SelectOption,
    ContainerComponentBuilder       as Container,
    SectionComponentBuilder         as Section,
    TextDisplayComponentBuilder     as Text,
    SeparatorComponentBuilder       as Separator,
    MediaGalleryComponentBuilder    as Media,
    MediaGalleryItemBuilder         as MediaItem,
    ThumbnailComponentBuilder       as Thumbnail,
    LinkButtonBuilder               as LinkButton,
    InteractiveButtonBuilder        as Button,
)


@clan.register()
class ListCommand(
    lightbulb.SlashCommand,
    name="list",
    description="Pick a clan to view or manage",
):
    # 1) define a user‐select option here:
    user = lightbulb.user(
        "discord-user",
        "Which user to show this for",
    )

    @lightbulb.invoke
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED,
    ) -> None:
        await ctx.defer(ephemeral=True)
        clan_data = await mongo.clans.find().to_list(length=None)
        clans     = [Clan(data=d) for d in clan_data]

        # Sort clans by activity/points for consistent ordering
        clans = sorted(clans, key=lambda c: c.points or 0, reverse=True)

        # Check if pagination is needed (Discord limit is 25 per dropdown)
        if len(clans) <= 25:
            # All clans fit in one dropdown - simple mode
            top_clans = clans
            remaining_clans = []
        else:
            # Too many clans - pagination mode
            top_clans = clans[:24]
            remaining_clans = clans[24:]

        options = []
        seen_tags = {}
        for c in top_clans:
            # Handle duplicate clan tags by making values unique
            if c.tag in seen_tags:
                seen_tags[c.tag] += 1
                unique_value = f"{c.tag}_{seen_tags[c.tag]}"
            else:
                seen_tags[c.tag] = 0
                unique_value = c.tag

            kwargs = {"label": c.name, "value": unique_value, "description": c.tag}
            if getattr(c, "partial_emoji", None):
                kwargs["emoji"] = c.partial_emoji
            options.append(SelectOption(**kwargs))

        action_id = str(uuid.uuid4())

        # Store remaining clans in button_store if they exist
        if remaining_clans:
            remaining_tags = [c.tag for c in remaining_clans]
            await mongo.button_store.insert_one({
                "_id": action_id,
                "command": "clan_browse",
                "user_id": ctx.member.id,
                "remaining_tags": remaining_tags,
                "page": 0
            })

        # Build component list
        component_list = [
            Text(content=(
                "## **Pick Your Clan**\n"
                "Use the dropdown below to select your clan.\n"
                "If your clan isn't listed, notify Ruggie."
            )),
            ActionRow(
                components=[
                    TextSelectMenu(
                        # 2) include the selected user's ID
                        custom_id=f"clan_select_menu:{action_id}_{self.user.id}",
                        placeholder="Select a clan",
                        max_values=1,
                        options=options,
                    )
                ]
            ),
        ]

        # Add "Show More" button if there are remaining clans
        if remaining_clans:
            component_list.append(
                ActionRow(
                    components=[
                        Button(
                            style=hikari.ButtonStyle.PRIMARY,
                            custom_id=f"clan_show_more:{action_id}",
                            label=f"Show More Clans ({len(remaining_clans)} more)",
                            emoji="🔍"
                        )
                    ]
                )
            )

        component_list.append(Media(items=[MediaItem(media="assets/Red_Footer.png")]))

        components = [
            Container(
                accent_color=RED_ACCENT,
                components=component_list,
            )
        ]
        await ctx.respond(components=components, ephemeral=True)


@register_action("clan_select_menu", no_return=True)
@lightbulb.di.with_di
async def on_clan_chosen(
    action_id: str,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    coc_client: coc.Client  = lightbulb.di.INJECTED,
    mongo: MongoClient      = lightbulb.di.INJECTED,
    **kwargs
):
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]
    _, user_id = action_id.rsplit("_", 1)
    user = await bot.rest.fetch_member(ctx.guild_id, int(user_id))

    selected_value = ctx.interaction.values[0]

    # Extract original tag from potentially modified value (remove _1, _2 etc.)
    tag = selected_value.split("_")[0] if "_" in selected_value else selected_value

    raw = await mongo.clans.find_one({"tag": tag})
    if not raw:
        return [
            Container(
                accent_color=RED_ACCENT,
                components=[Text(content="⚠️ I couldn’t find that clan in our database.")]
            )
        ]
    db_clan = Clan(data=raw)

    api_clan = None
    try:
        api_clan = await coc_client.get_clan(tag=tag)
    except coc.NotFound:
        pass

    if api_clan and api_clan.capital_districts:
        peak = max(d.hall_level for d in api_clan.capital_districts)
    else:
        peak = 0

    lines = [
        f"{emojis.red_arrow_right}**Name:** {db_clan.name} (`{db_clan.tag}`)",
        f"{emojis.red_arrow_right}**Level:** {api_clan.level}" if api_clan else "• **Level:** —",
        f"{emojis.red_arrow_right}**CWL Rank:** {api_clan.war_league.name if api_clan else '—'}",
        f"{emojis.red_arrow_right}**Type:** {db_clan.type or '—'}",
        f"{emojis.red_arrow_right}**Capital Peak:** Level {peak}",
    ]
    content = (
        f"Hey {user.mention},\n"
        f"I’d like to introduce you to **{db_clan.name}**, led by "
        f"<@{db_clan.leader_id}> and <@&{db_clan.leader_role_id}>."
    )
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=f"Hey {user.mention},"),
                Text(content=(
                    f"I’d like to introduce you to **{db_clan.name}**, led by "
                    f"<@{db_clan.leader_id}> and <@&{db_clan.leader_role_id}>."
                )),
                Separator(divider=True),
                Text(content="## **Important Information Below**"),
                Text(content=(
                    "You’re free to move temporarily within our Family. "
                    "If you want to switch clans permanently, please discuss it with leadership to ensure a good fit.\n\n"
                    "If you’re unhappy with the clan given, let us know—we can explore other options."
                )),
                Separator(divider=True),
                Text(content=(
                    f"From now on, **{db_clan.name}** is your new home. "
                    "Use the code `Arcane` to access any clan within our Family. "
                    "It will become your friend during CWL... *make sense?*"
                )),
            ],
        ),
        Container(
            accent_color=RED_ACCENT,
            components=[
                Section(
                    components=[Text(content="\n".join(lines))],
                    accessory=Thumbnail(media=api_clan.badge.large if api_clan else db_clan.logo),
                ),
                Media(items=[MediaItem(media=db_clan.banner if db_clan.banner and db_clan.banner != '.' else "assets/Red_Footer.png")]),
                ActionRow(
                    components=[
                        LinkButton(
                            label="Open In-Game",
                            url=api_clan.share_link if api_clan else ""
                        )
                    ]
                ),
                Separator(divider=True),
                Text(content=f"-# Requested by {ctx.member.mention}"),
            ],
        ),
    ]

    await ctx.interaction.delete_initial_response()

    await bot.rest.create_message(
        channel=ctx.channel_id,
        components=components,
        user_mentions = [user.id, db_clan.leader_id],
        role_mentions = True,
    )


@register_action("clan_show_more", no_return=True)
@lightbulb.di.with_di
async def on_clan_show_more(
    action_id: str,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    mongo: MongoClient      = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle 'Show More' button click to display paginated clan list."""
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]

    # Fetch stored data
    stored_data = await mongo.button_store.find_one({"_id": action_id})
    if not stored_data:
        await ctx.interaction.edit_initial_response(
            components=[
                Container(
                    accent_color=RED_ACCENT,
                    components=[Text(content="⚠️ Session expired. Please run the command again.")]
                )
            ]
        )
        return

    remaining_tags = stored_data.get("remaining_tags", [])
    current_page = stored_data.get("page", 0)
    user_id = stored_data.get("user_id")

    # Fetch clan data for remaining tags
    clan_data = await mongo.clans.find({"tag": {"$in": remaining_tags}}).to_list(length=None)
    remaining_clans = [Clan(data=d) for d in clan_data]

    # Sort by original order (already sorted by points)
    remaining_clans = sorted(
        remaining_clans,
        key=lambda c: remaining_tags.index(c.tag) if c.tag in remaining_tags else 999
    )

    # Pagination - treat dropdown as page 1, this view as page 2+
    clans_per_page = 25
    total_clans_in_db = len(remaining_clans) + 24  # Include the 24 clans shown in dropdown
    remaining_pages = (len(remaining_clans) + clans_per_page - 1) // clans_per_page
    total_pages = 1 + remaining_pages  # +1 for the dropdown page
    current_page = max(0, min(current_page, remaining_pages - 1))
    display_page = current_page + 2  # +2 because dropdown is page 1, this starts at page 2

    # Calculate indices for display (relative to clans_on_page array)
    start_idx_in_array = current_page * clans_per_page
    end_idx_in_array = min(start_idx_in_array + clans_per_page, len(remaining_clans))
    clans_on_page = remaining_clans[start_idx_in_array:end_idx_in_array]

    # Calculate indices for display text (relative to ALL clans including dropdown)
    start_idx_display = 24 + (current_page * clans_per_page)  # Start after dropdown's 24 clans
    end_idx_display = start_idx_display + len(clans_on_page)

    # Build options for current page
    options = []
    seen_tags = {}
    for c in clans_on_page:
        if c.tag in seen_tags:
            seen_tags[c.tag] += 1
            unique_value = f"{c.tag}_{seen_tags[c.tag]}"
        else:
            seen_tags[c.tag] = 0
            unique_value = c.tag

        kwargs = {"label": c.name, "value": unique_value, "description": c.tag}
        if getattr(c, "partial_emoji", None):
            kwargs["emoji"] = c.partial_emoji
        options.append(SelectOption(**kwargs))

    # Build components
    component_list = [
        Text(content=f"## **Browse All Clans**"),
        Text(content=f"**Page {display_page} of {total_pages}** • Showing clans {start_idx_display + 1}-{end_idx_display} of {total_clans_in_db} total"),
        Separator(divider=True),
        ActionRow(
            components=[
                TextSelectMenu(
                    custom_id=f"clan_select_menu:{action_id}_{user_id}",
                    placeholder="Select a clan",
                    max_values=1,
                    options=options,
                )
            ]
        ),
    ]

    # Always add navigation buttons (back button + pagination if needed)
    navigation_buttons = []

    # Always show "Back to List" button
    navigation_buttons.append(
        Button(
            style=hikari.ButtonStyle.PRIMARY,
            custom_id=f"clan_back_to_list:{action_id}",
            label="Back to List",
            emoji="⬅️"
        )
    )

    # Add pagination buttons if multiple pages of remaining clans
    if remaining_pages > 1:
        if current_page > 0:
            navigation_buttons.append(
                Button(
                    style=hikari.ButtonStyle.SECONDARY,
                    custom_id=f"clan_browse_prev:{action_id}",
                    label="Previous",
                    emoji="◀️"
                )
            )

        if current_page < remaining_pages - 1:
            navigation_buttons.append(
                Button(
                    style=hikari.ButtonStyle.SECONDARY,
                    custom_id=f"clan_browse_next:{action_id}",
                    label="Next",
                    emoji="▶️"
                )
            )

    component_list.append(
        ActionRow(components=navigation_buttons)
    )

    component_list.append(Media(items=[MediaItem(media="assets/Red_Footer.png")]))

    await ctx.interaction.edit_initial_response(
        components=[
            Container(
                accent_color=RED_ACCENT,
                components=component_list
            )
        ]
    )


@register_action("clan_browse_next", no_return=True)
@lightbulb.di.with_di
async def on_clan_browse_next(
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle 'Next Page' button click."""
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]

    # Update page in button_store
    stored_data = await mongo.button_store.find_one({"_id": action_id})
    if stored_data:
        current_page = stored_data.get("page", 0)
        await mongo.button_store.update_one(
            {"_id": action_id},
            {"$set": {"page": current_page + 1}}
        )

    # Re-render with new page
    await on_clan_show_more(action_id, mongo=mongo, ctx=ctx)


@register_action("clan_browse_prev", no_return=True)
@lightbulb.di.with_di
async def on_clan_browse_prev(
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle 'Previous Page' button click."""
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]

    # Update page in button_store
    stored_data = await mongo.button_store.find_one({"_id": action_id})
    if stored_data:
        current_page = stored_data.get("page", 0)
        await mongo.button_store.update_one(
            {"_id": action_id},
            {"$set": {"page": max(0, current_page - 1)}}
        )

    # Re-render with new page
    await on_clan_show_more(action_id, mongo=mongo, ctx=ctx)


@register_action("clan_back_to_list", no_return=True)
@lightbulb.di.with_di
async def on_clan_back_to_list(
    action_id: str,
    mongo: MongoClient = lightbulb.di.INJECTED,
    **kwargs
):
    """Handle 'Back to List' button click - return to dropdown view."""
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]

    # Fetch stored data to get user_id
    stored_data = await mongo.button_store.find_one({"_id": action_id})
    if not stored_data:
        await ctx.interaction.edit_initial_response(
            components=[
                Container(
                    accent_color=RED_ACCENT,
                    components=[Text(content="⚠️ Session expired. Please run the command again.")]
                )
            ]
        )
        return

    user_id = stored_data.get("user_id")

    # Re-fetch and rebuild original dropdown view
    clan_data = await mongo.clans.find().to_list(length=None)
    clans = [Clan(data=d) for d in clan_data]

    # Sort clans by activity/points for consistent ordering
    clans = sorted(clans, key=lambda c: c.points or 0, reverse=True)

    # Check if pagination is needed (Discord limit is 25 per dropdown)
    if len(clans) <= 25:
        top_clans = clans
        remaining_clans = []
    else:
        top_clans = clans[:24]
        remaining_clans = clans[24:]

    # Build options for dropdown
    options = []
    seen_tags = {}
    for c in top_clans:
        if c.tag in seen_tags:
            seen_tags[c.tag] += 1
            unique_value = f"{c.tag}_{seen_tags[c.tag]}"
        else:
            seen_tags[c.tag] = 0
            unique_value = c.tag

        kwargs_dict = {"label": c.name, "value": unique_value, "description": c.tag}
        if getattr(c, "partial_emoji", None):
            kwargs_dict["emoji"] = c.partial_emoji
        options.append(SelectOption(**kwargs_dict))

    # Update remaining_tags in button_store
    if remaining_clans:
        remaining_tags = [c.tag for c in remaining_clans]
        await mongo.button_store.update_one(
            {"_id": action_id},
            {"$set": {"remaining_tags": remaining_tags, "page": 0}}
        )

    # Build component list
    component_list = [
        Text(content=(
            "## **Pick Your Clan**\n"
            "Use the dropdown below to select your clan.\n"
            "If your clan isn't listed, notify Ruggie."
        )),
        ActionRow(
            components=[
                TextSelectMenu(
                    custom_id=f"clan_select_menu:{action_id}_{user_id}",
                    placeholder="Select a clan",
                    max_values=1,
                    options=options,
                )
            ]
        ),
    ]

    # Add "Show More" button if there are remaining clans
    if remaining_clans:
        component_list.append(
            ActionRow(
                components=[
                    Button(
                        style=hikari.ButtonStyle.PRIMARY,
                        custom_id=f"clan_show_more:{action_id}",
                        label=f"Show More Clans ({len(remaining_clans)} more)",
                        emoji="🔍"
                    )
                ]
            )
        )

    component_list.append(Media(items=[MediaItem(media="assets/Red_Footer.png")]))

    await ctx.interaction.edit_initial_response(
        components=[
            Container(
                accent_color=RED_ACCENT,
                components=component_list,
            )
        ]
    )


# Note: loader.command(clan) is now called once in clan/__init__.py
