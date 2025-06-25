

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
        self.white_arrow_right = EmojiType("<:aa_a_w:1036081848633282691>")
        self.purple_arrow_right = EmojiType("<:aa_a_p:1033739074604896257>")

emojis = Emojis()







