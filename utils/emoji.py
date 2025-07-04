

import hikari


class EmojiType:
    def __init__(self, emoji_string):
        self.emoji_string = emoji_string
        self.str = emoji_string

    def __str__(self):
        return self.emoji_string

    @property
    def partial_emoji(self):
        emoji = self.emoji_string.split(':')
        animated = '<a:' in self.emoji_string
        emoji = hikari.CustomEmoji(
            name=emoji[1][1:],
            id=hikari.Snowflake(int(str(emoji[2])[:-1])),
            is_animated=animated
        )
        return emoji

class Emojis:
    def __init__(self):
        self.blank = EmojiType("<:Blank:1035193835225096356>")
        self.white_arrow_right = EmojiType("<:Arrow_White:1387845178039206019>")
        self.purple_arrow_right = EmojiType("<:Arrow_Purple:1387846287176761346>")
        self.red_arrow_right = EmojiType("<:Arrow_Red:1387845254580932769>")
        self.gold_arrow_right = EmojiType("<:Arrow_Gold:1387845312852398082>")
        self.add = EmojiType("<:Add:1387844836916199466>")
        self.remove = EmojiType("<:Remove:1387844866008027229>")
        self.edit = EmojiType("<:Edit:1387850342473011481>")
        self.view = EmojiType("<:View:1387842874053234808>")
        self.confirm = EmojiType("<:Confirm:1387845018139754517>")
        self.cancel = EmojiType("<:Cancel:1387845041845698652>")

        # TH Emojis
        self.TH2 = EmojiType("<:TH_2:1387845120732172329>")
        self.TH3 = EmojiType("<:TH_3:1387842982333644903>")
        self.TH4 = EmojiType("<:TH_4:1387844251731103884>")
        self.TH5 = EmojiType("<:TH_5:1387844290612559933>")
        self.TH6 = EmojiType("<:TH_6:1387844317476819074>")
        self.TH7 = EmojiType("<:TH_7:1387844342156099716>")
        self.TH8 = EmojiType("<:TH_8:1387844362309992683>")
        self.TH9 = EmojiType("<:TH_9:1387844388675387513>")
        self.TH10 = EmojiType("<:TH_10:1387844411609845861>")
        self.TH11 = EmojiType("<:TH_11:1387844434296836276>")
        self.TH12 = EmojiType("<:TH_12:1387844458690904245>")
        self.TH13 = EmojiType("<:TH_13:1387844480849149983>")
        self.TH14 = EmojiType("<:TH_14:1387844504014295101>")
        self.TH15 = EmojiType("<:TH_15:1387844534729314344>")
        self.TH16 = EmojiType("<:TH_16:1387844562059395193>")
        self.TH17 = EmojiType("<:TH_17:1387844788853801081>")

emojis = Emojis()







