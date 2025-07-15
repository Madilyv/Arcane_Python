# extensions/events/message/ticket_automation/fwa/components/fwa_templates.py
"""
Message templates for FWA automation flow.
These templates define the structure and content for each FWA step.
"""

# War weight request template
WAR_WEIGHT_REQUEST_TEMPLATE = {
    "title": "## ⚖️ **War Weight Check**",
    "content": (
        "We need your **current war weight** to ensure fair matchups. Please:\n\n"
        "{red_arrow} **Post** a Friendly Challenge in-game.\n"
        "{red_arrow} **Scout** that challenge you posted\n"
        "{red_arrow} **Tap** on your Town Hall, then hit **Info**.\n"
        "{red_arrow} **Upload** a screenshot of the Town Hall info popup here.\n\n"
        "*See the example below for reference.*"
    ),
    "footer": "Waiting for your war weight screenshot...",
    "image_url": "https://res.cloudinary.com/dxmtzuomk/image/upload/v1751550804/TH_Weight.png",
    "footer_image": "assets/Gold_Footer.png"
}

# FWA explanation template
FWA_EXPLANATION_TEMPLATE = {
    "title": "## 🏰 **What is FWA?**",
    "content": (
        "**FWA** stands for **Farm War Alliance**, a community within Clash of Clans where "
        "clans synchronize to match each other in wars.\n\n"
        "{red_arrow} **Primary goal:** Win wars easily for loot\n"
        "{red_arrow} **Bases:** Must be FWA-approved (we provide these)\n"
        "{red_arrow} **Heroes:** Can be upgrading during war\n"
        "{red_arrow} **Attacks:** Specific targets assigned\n"
        "{red_arrow} **Outcome:** Predetermined winner/loser\n\n"
        "**Benefits:**\n"
        "• Easy war loot without effort\n"
        "• No pressure to perform\n"
        "• Heroes can always upgrade\n"
        "• Relaxed war environment\n\n"
        "_FWA is perfect for farmers who want war loot without the competitive stress!_"
    ),
    "footer": None,
    "instruction": "💡 **To continue, type:** `Understood`",
    "footer_image": "assets/Gold_Footer.png"
}

# Lazy CWL explanation template
LAZY_CWL_TEMPLATE = {
    "title": "## 🏅 **Heard of Lazy CWL?**",
    "content": (
        "**We do CWL the LAZY WAY!** Here's what that means:\n\n"
        "{red_arrow} **15v15 Format Only** - Maximum medals\n"
        "{red_arrow} **Heroes can upgrade** - No waiting!\n"
        "{red_arrow} **Use ALL attacks** - Even with heroes down\n"
        "{red_arrow} **Hit your mirror** - Same position as you\n"
        "{red_arrow} **One-star minimum** - Easy requirement\n\n"
        "**The Strategy:**\n"
        "• Drop heroes (even if upgrading)\n"
        "• Use minimal troops\n"
        "• Get one star\n"
        "• Collect medals\n"
        "• Repeat!\n\n"
        "**Why Lazy CWL?**\n"
        "✅ Maximum medal rewards\n"
        "✅ No stress or pressure\n"
        "✅ Heroes always upgrading\n"
        "✅ Perfect for farmers\n\n"
        "_Remember: In our FWA operation, it's **LAZY WAY or NO WAY!**_"
    ),
    "footer": None,
    "instruction": "💡 **To continue, type:** `Understood`",
    "footer_image": "assets/Gold_Footer.png"
}

# Agreement template
AGREEMENT_TEMPLATE = {
    "title": "## 🤝 **Final Confirmation**",
    "content": (
        "Do you **truly understand** Lazy CWL and agree that when in our "
        "FWA operation it is:\n\n"
        "# **LAZY WAY or NO WAY!**\n\n"
        "This means:\n"
        "• You'll use the FWA base we provide\n"
        "• You'll follow all FWA rules\n"
        "• You'll participate in Lazy CWL\n"
        "• You understand the relaxed approach\n\n"
        "_This is your commitment to the FWA lifestyle!_"
    ),
    "gif_url": "https://c.tenor.com/-IE-fH9z1CwAAAAd/tenor.gif",
    "footer": None,
    "instruction": "✅ **To continue, type:** `I agree`",
    "footer_image": "assets/Gold_Footer.png"
}

# FWA completion template
FWA_COMPLETION_TEMPLATE = {
    "title": "## 🏰 **Application Complete!**",
    "content": (
        "**The FWA Leaders are Reviewing Your Application**\n\n"
        "Please be patient as this process may take some time. "
        "Leaders will also need to evaluate roster adjustments to "
        "accommodate your application.\n\n"
        "We kindly ask that you **do not ping anyone** during this time. "
        "Rest assured, we are aware of your presence and will update you "
        "as soon as possible.\n\n"
        "_Thank you for your interest in joining our FWA operation!_"
    ),
    "footer": None,
    "footer_image": "assets/Gold_Footer.png"
}