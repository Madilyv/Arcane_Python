

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

emojis = Emojis()







