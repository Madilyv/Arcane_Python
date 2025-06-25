
class Clan:
    def __init__(self, data: dict):
        self._data = data
        self.announcement_id: int = data.get("announcement_id")
        self.chat_channel_id: int = data.get("chat_channel_id")
        self.emoji: str = data.get("emoji")
        self.tag: str = data.get("tag")
        self.leader_id: int = data.get("leader_id")
        self.leader_role_id: int = data.get("leader_role_id")
        self.leadership_channel_id: int = data.get("leadership_channel_id")
        self.logo: str = data.get("logo")
        self.name: str = data.get("name")
        self.profile: str = data.get("profile")
        self.role_id: int = data.get("role_id")
        self.rules_channel_id: int = data.get("rules_channel_id")
        self.status: str = data.get("status")
        self.th_attribute: str = data.get("th_attribute")
        self.th_requirements: int = data.get("th_requirements")
        self.thread_id = data.get("thread_id")
        self.type: str = data.get("type")