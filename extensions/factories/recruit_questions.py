import lightbulb
import asyncio
import hikari
from aiohttp.web_routedef import delete
from hikari import GatewayBot
from hikari.api import LinkButtonBuilder
from hikari.impl import (
    MessageActionRowBuilder as ActionRow,
    TextSelectMenuBuilder as TextSelectMenu,
    SelectOptionBuilder as SelectOption,
    ContainerComponentBuilder as Container,
    SectionComponentBuilder as Section,
    InteractiveButtonBuilder as Button,
    TextDisplayComponentBuilder as Text,
    SeparatorComponentBuilder as Separator,
    ThumbnailComponentBuilder as Thumbnail,
    MediaGalleryComponentBuilder as Media,
    MediaGalleryItemBuilder as MediaItem,
)
from lightbulb.components import LinkButton
from utils.constants import RED_ACCENT
from utils.emoji import emojis
from extensions.components import register_action

@register_action("primary_questions", no_return=True)
@lightbulb.di.with_di
async def primary_questions(
    user_id: int,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):

    ctx: lightbulb.components.MenuContext = kwargs.get("ctx")
    choice = ctx.interaction.values[0]
    user = await bot.rest.fetch_member(ctx.guild_id, user_id)

    if choice == "attack_strategies":
        components = [
            Text(content=f"⚔️ **Attack Strategy Breakdown** · {user.mention}"),
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        "Help us understand your go-to attack strategies!\n\n"
                        f"{emojis.red_arrow_right} **Main Village strategies**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. Hybrid, Queen Charge w/ Hydra, Lalo_\n\n"
                        f"{emojis.red_arrow_right} **Clan Capital Attack Strategies**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. Super Miners w/ Freeze_\n\n"
                        f"{emojis.red_arrow_right} **Highest Clan Capital Hall level you’ve attacked**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. CH 8, CH 9, etc.\n\n_"
                        "*Your detailed breakdown helps us match you to the perfect clan!*"
                    )),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                    ]),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ]
            )
        ]

    elif choice == "future_clan_expectations":
        components = [
            Text(content=f"🔮 **Future Clan Expectations** · {user.mention}"),
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content=(
                        "Help us tailor your clan experience! Please answer the following:\n\n"
                        f"{emojis.red_arrow_right} **What do you expect from your future clan?**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _(e.g., Active wars, good communication, strategic support._)\n\n"
                        f"{emojis.red_arrow_right} **Minimum clan level you’re looking for?**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. Level 5, Level 10_\n\n"
                        f"{emojis.red_arrow_right}  **Minimum Clan Capital Hall level?**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. CH 8 or higher_\n\n"
                        f"{emojis.red_arrow_right} **CWL league preference?**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} _e.g. Crystal league or no preference_\n\n"
                        f"{emojis.red_arrow_right} **Preferred playstyle?**\n"
                        f"{emojis.blank}{emojis.white_arrow_right} Competitive\n"
                        f"{emojis.blank}{emojis.white_arrow_right} Casual\n"
                        f"{emojis.blank}{emojis.white_arrow_right} Zen _Type __What is Zen__ to learn more._\n"
                        f"{emojis.blank}{emojis.white_arrow_right} FWA _Type __What is FWA__ to learn more._\n"
                    )),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                    ]),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ]
            )
        ]
    elif choice == "discord_basic_skills":
        components = [
        Text(content=f"🎓 **Discord Basics Check** · {user.mention}"),

        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(
                    content=(
                        "Hey there! Before we proceed, let's confirm you’re comfy with our core Discord features:\n\n"
                        "1️⃣ **React** to this message with any emoji of your choice.\n"
                        "2️⃣ **Mention** your recruiter in this thread (e.g. <@1386722406051217569>).\n\n"
                        "*These steps help us make sure you can react and ping others; key skills for smooth clan comms!*"
                    )
                ),
                Media(
                    items=[
                        MediaItem(media="https://c.tenor.com/oEkj7apTtT4AAAAC/tenor.gif"),
                ]),
                Text(content=f"_Requested by {ctx.user.display_name}_")
            ]
        ),
    ]
    elif choice == "discord_basic_skills_2":
        components = [
        Text(content=f"🎯 **Master Discord Communication** · {user.mention}"),

        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(
                    content=(
                        "In **Kings**, we rely heavily on two key Discord skills:\n\n"
                        "🔔 **Mentions** (pings) – call out a member or a role to grab attention.\n"
                        "👍 **Reactions** – respond quickly with an emoji to acknowledge messages.\n\n"
                        "*These are the fastest ways to keep our clan chat flowing!*"
                    )
                ),

                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png"),
                ]),

                Text(content=f"_Requested by {ctx.user.display_name}_")
            ]
        ),
    ]
    elif choice == "age_bracket_&_timezone":
        components = [
            Text(content=f"⏳ **What's Your Age Bracket?** · {user.mention}"),

            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(content="**What age bracket do you fall into?**\n\n"),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right}"
                                    "**16 & Under** *(Family-Friendly Clan)*"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧒16 & Under",
                            custom_id=f"age:16_under_{user.id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right}"
                                    "**17 – 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧑17 – 25",
                            custom_id=f"age:17_25_{user.id}",
                        ),
                    ),
                    Section(
                        components=[
                            Text(
                                content=(
                                    f"{emojis.white_arrow_right}"
                                    "**Over 25**"
                                )
                            )
                        ],
                        accessory=Button(
                            style=hikari.ButtonStyle.SECONDARY,
                            label="🧓Over 25",
                            custom_id=f"age:over_25_{user.id}",
                        ),
                    ),

                    Text(content="*Don’t worry, we’re not knocking on your door! Just helps us get to know you better. 😄👍*"),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                    ]),
                    Text(content=f"_Requested by {ctx.user.display_name}_"),
                ]
            ),

        ]
    elif choice == "leaders_checking_you_out":
        components = [
            # Ping + headline
            Text(content=f"🔍 **Application Under Review** · {user.mention}"),

            # Main card
            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(
                        content=(
                            "Thank you for completing your application! 🎉\n\n"
                            "Our leadership team is now reviewing your responses to find the perfect clan match. "
                            "Please sit tight, we’ll be with you shortly! ⏳\n\n"
                            "We truly appreciate your interest in the Kings Alliance and can’t wait to welcome you aboard!"
                        )
                    ),
                    Media(
                        items=[
                            MediaItem(media="assets/Red_Footer.png"),
                        ]),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ]
            )
        ]

    await bot.rest.create_message(
        components=components,
        channel=ctx.channel_id
    )
    await asyncio.sleep(20)
    action_id = ctx.interaction.custom_id.split(":", 1)[1]
    new_components = await recruit_questions_page(
        action_id=action_id,
        user_id=user_id,
        ctx=ctx,
    )
    await ctx.interaction.delete_initial_response()
    await ctx.respond(
        components=new_components,
        ephemeral=True,
    )
    ## If I decide to edit instead of deleting and resending
    #await ctx.interaction.edit_initial_response(components=new_components)

@register_action("age", no_return=True)
@lightbulb.di.with_di
async def on_age_button(
    action_id: str,
    bot: GatewayBot = lightbulb.di.INJECTED,
    **kwargs
):
    ctx: lightbulb.components.MenuContext = kwargs["ctx"]
    bracket, user_id = action_id.rsplit("_", 1)
    user_id = int(user_id)
    user = await bot.rest.fetch_member(ctx.guild_id, user_id)

    if int(ctx.user.id) != user_id:
        await ctx.respond(
            f"Sorry {ctx.user.mention}, this button is only for {user.mention} to click. Please let them continue!",
            ephemeral=True
        )
        return

    await ctx.interaction.delete_initial_response()

    if bracket == "16_under":
        components = [
            Text(content=f"🎉 **16 & Under Registered!** · {user.mention}"),

            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(
                        content=(
                            "Got it! You're bringing that youthful energy!\n\n"
                            "We'll find you a family-friendly clan that's the perfect fit for you.\n\n"
                        )
                    ),
                    Media(
                        items=[
                            MediaItem(media="https://c.tenor.com/oxxT2JPSQccAAAAC/tenor.gif"),
                        ]
                    ),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ],
            )]
        await bot.rest.create_message(
            components=components,
            channel=ctx.channel_id
        )
    elif bracket == "17_25":
        components = [
            Text(content=f"🎮 **17–25 Confirmed** · {user.mention}"),

            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(
                        content=(
                            "Understood! You’re in prime gaming years!\n\n"
                            "Time to conquer the Clash world! 🏆\n\n"
                        )
                    ),
                    Media(
                        items=[
                            MediaItem(media="https://c.tenor.com/twdtlMLE8UIAAAAC/tenor.gif"),
                        ]
                    ),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ],
        )]
        await bot.rest.create_message(
            components=components,
            channel=ctx.channel_id
        )
    elif bracket == "over_25":
        components = [
            Text(content=f"🏅 **Age Locked In** · {user.mention}"),

            Container(
                accent_color=RED_ACCENT,
                components=[
                    Text(
                        content=(
                            "Awesome! Experience meets strategy!\n\n"
                            "Welcome to the veteran league of Clashers! 💪\n\n"
                        )
                    ),
                    Media(
                        items=[
                            MediaItem(media="https://c.tenor.com/m6o-4dKGdVAAAAAC/tenor.gif"),
                        ]
                    ),
                    Text(content=f"_Requested by {ctx.user.display_name}_")
                ],
        )]
        await bot.rest.create_message(
            components=components,
            channel=ctx.channel_id
        )
    await asyncio.sleep(10)
    components = [
        Text(content=f"🌐 **Set Your Time Zone** · {user.mention}"),

        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(
                    content=(
                        "To help us match you with the right clan and events, let’s set your timezone.\n\n"
                        "**Check your zone here:** [Time Zone Map](https://zones.arilyn.cc/)\n"
                        "**Example format:** `America/New_York`\n\n"
                        "Then simply type your timezone in chat, quick and easy!"
                    )
                ),
                # Section(
                #     components=[
                #         Text(
                #             content=(
                #                 f"{emojis.white_arrow_right}"
                #                 "**Check your zone here:**"
                #             )
                #         )
                #     ],
                #     accessory=LinkButton(
                #         url="https://zones.arilyn.cc/",
                #         label="**Check your zone here:**",
                #         emoji=None,
                #         disabled=False
                #     ),
                # ),
                # LinkButton(
                #     url="https://zones.arilyn.cc/",
                #     label="**Check your zone here:**",
                # ),
                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png"),
                ]),
                Text(content="_Kings Alliance Recruitment – Syncing Schedules, Building Teams!_")
            ],
        )]
    await bot.rest.create_message(
        components=components,
        channel=ctx.channel_id
    )

async def recruit_questions_page(
    action_id: str,
    user_id: int,
    **kwargs
):
    components = [
        Container(
            accent_color=RED_ACCENT,
            components=[
                Text(content=(
                    "An all-in-one toolkit to efficiently recruit candidates into the Kings Alliance.\n\n"
                    f"{emojis.red_arrow_right} Primary Questions: Send tailored candidate questions.\n"
                    f"{emojis.red_arrow_right} Explanations: Summarise FWA, Zen & Alliance essentials.\n"
                    f"{emojis.red_arrow_right} FWA Questions: Send core FWA questions.\n"
                    f"{emojis.red_arrow_right} Keep It Moving: Send quick “hurry up” GIFs.\n\n"
                    "Stay organized, efficient, and aligned with Kings recruitment standards.\n\n"
                )),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            max_values=1,
                            custom_id=f"primary_questions:{action_id}",
                            placeholder="Primary Questions",
                            options=[
                                SelectOption(
                                    emoji=1387846413211402352,
                                    label="Attack Strategies",
                                    value="attack_strategies"),
                                SelectOption(
                                    emoji=1387846432316194837,
                                    label="Future Clan Expectations",
                                    value="future_clan_expectations"),
                                SelectOption(
                                    emoji=1387846461672132649,
                                    label="Discord Basic Skills",
                                    value="discord_basic_skills"),
                                SelectOption(
                                    emoji=1387846482220159168,
                                    label="Discord Basic Skills pt.2",
                                    value="discord_basic_skills_2"),
                                SelectOption(
                                    emoji=1387846506589061220,
                                    label="Age Bracket & Timezone",
                                    value="age_bracket_&_timezone"),
                                SelectOption(
                                    emoji=1387846529229787246,
                                    label="Leaders Checking You Out",
                                    value="leaders_checking_you_out"),
                    ]),
                ]),
                Text(content="-# Kings Alliance - Where Legends Are Made"),
                Media(
                    items=[
                        MediaItem(media="assets/Red_Footer.png")
                ]),
            ]),
        ]

    return components
