# extensions/commands/howto/link.py
"""
How to link your Clash of Clans account - for those who need EXTRA help.
"""

import hikari
import lightbulb
from . import loader, howto

@howto.register()
class Link(
    lightbulb.SlashCommand,
    name="link",
    description="Learn how to link your Clash account (yes, it's THAT easy)",
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ) -> None:
        # Create embeds with progressively happier colors (red -> orange -> yellow -> light green -> green)
        embeds = []
        
        # Embed 1: Find your profile
        embed1 = hikari.Embed(
            title="👆 Step 1 • Click Your Profile",
            description=(
                "Tap the little player icon in the **TOP-LEFT** of your game screen.\n\n"
                "🎯 **PRO TIP:** It's literally in the corner. You can't miss it!\n"
                "Look for your Town Hall level - that's YOUR profile! 🏰"
            ),
            color=0xFF6B6B  # Soft red
        )
        embed1.set_image("https://res.cloudinary.com/dxmtzuomk/image/upload/v1753958600/misc_images/How-Tos/Profile.jpg")
        embed1.set_footer("Don't worry, we believe in you! 💪")
        embeds.append(embed1)
        
        # Embed 2: Copy your tag
        embed2 = hikari.Embed(
            title="📋 Step 2 • Copy Your Tag",
            description=(
                "Hit the **Share** button, then press **Copy** to grab your player tag!\n\n"
                "⚠️ **SUPER IMPORTANT:** Your tag looks like `#ABC123XYZ`\n"
                "👉 YES, you NEED the # symbol!\n"
                "👉 NO spaces, just copy it exactly!\n\n"
                "**Example:** `#RU0OV8UP` ✅"
            ),
            color=0xFFAA5B  # Orange
        )
        embed2.set_image("https://res.cloudinary.com/dxmtzuomk/image/upload/v1753958600/misc_images/How-Tos/Profile_01.jpg")
        embed2.set_footer("You're doing great! Almost there! 🚀")
        embeds.append(embed2)
        
        # Embed 3: Run the command
        embed3 = hikari.Embed(
            title="⌨️ Step 3 • Run the /link Command",
            description=(
                "In Discord, type **EXACTLY** this:\n\n"
                "```/link player:#YOURTAG```\n\n"
                "Remember:\n"
                "• Start with `/link` (with the slash!)\n"
                "• Then type `player:`\n"
                "• Paste your tag right after the colon\n"
                "• NO SPACES between : and #"
            ),
            color=0xFFD93D  # Yellow
        )
        embed3.set_image("https://res.cloudinary.com/dxmtzuomk/image/upload/v1753958599/misc_images/How-Tos/link.jpg")
        embed3.set_footer("So close! You've got this, champ! 🏆")
        embeds.append(embed3)
        
        # Embed 4: Press enter
        embed4 = hikari.Embed(
            title="✅ Step 4 • Press Enter",
            description=(
                "Hit **Enter** and... 🥁🥁🥁\n\n"
                "# 🎉 CONGRATULATIONS! 🎉\n\n"
                "Your Clash account is now linked! 🎊\n\n"
                "You're officially a **DISCORD GENIUS!** 🧠✨\n"
                "Give yourself a pat on the back! 👏"
            ),
            color=0x6BCF7F  # Light green
        )
        embed4.set_image("https://res.cloudinary.com/dxmtzuomk/image/upload/v1753958600/misc_images/How-Tos/Link_Successful.jpg")
        embed4.set_footer("We knew you could do it! 🌟")
        embeds.append(embed4)
        
        # Embed 5: Celebration
        embed5 = hikari.Embed(
            title="🤔 Was That So Hard?",
            description=(
                "Look at you, linking accounts like a **PRO!** 😎\n\n"
                "Now you can:\n"
                "• Flex your base in Discord 💪\n"
                "• Join awesome clans 🏰\n"
                "• Show off your achievements 🏆\n\n"
                "**Welcome to the club, legend!** 🎮"
            ),
            color=0x4CAF50  # Full green - success!
        )
        embed5.set_image("https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2c3emQ1ejJyeWV3enhhbHJhMmlmdGViaWVpd2xrcGhudDM2OHc0OSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/NaboQwhxK3gMU/giphy.gif")
        embed5.set_footer("You're amazing! Don't let anyone tell you otherwise! ❤️")
        embeds.append(embed5)
        
        # Send to the channel for everyone to see
        await bot.rest.create_message(
            channel=ctx.channel_id,
            embeds=embeds
        )
        
        # Confirm to the user who ran the command
        await ctx.respond("✅ How-to guide posted!", ephemeral=True)