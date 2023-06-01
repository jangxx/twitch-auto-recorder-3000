import logging
from typing import List
from config import Config

from twitchAPI.twitch import Twitch

from plugins.plugin_base import Plugin
from lib.service_base import ServiceBase
from services.twitch_recorder import TwitchRecorder

log = logging.getLogger(__file__)

class TwitchService(ServiceBase):
    def __init__(self):
        super().__init__()

        self._twitch: Twitch
        self._streams = {}

        self._output_path = None
        self._streamlink_options = None

    def init(self, config: Config):
        if config.value(["twitch", "clientid"]) is None or config.value(["twitch", "secret"]) is None:
            log.info("Twitch API credentials not found, Twitch service is not going to be loaded")
            return False

        self._twitch = Twitch( config.value(["twitch", "clientid"]), config.value(["twitch", "secret"]) )
        self._output_path = config.value("output_path")
        self._streamlink_options = config.value("streamlink_options")

        return True

    def is_user_live(self, username: str) -> bool:
        return (username in self._streams and self._streams[username]["type"] == "live")
    
    def update_streams(self, usernames: List[str]):
        if not self.initialized:
            return 0

        self._streams = {}
        remaining_usernames = list(u.lower() for u in usernames)
        cursor = None

        while len(remaining_usernames) > 0:
            resp = self._twitch.get_streams(
                after=cursor,
                first = 100,
                user_login=remaining_usernames[:100]
            )

            for stream in resp["data"]:
                self._streams[stream["user_login"]] = stream

            remaining_usernames = remaining_usernames[100:]

        return len(self._streams)

    def get_recorder(self, username: str, params: List[str], plugins: List[Plugin]) -> TwitchRecorder:
        quality = "best"
        if len(params) > 0:
            quality = params[0]

        return TwitchRecorder(username, quality, self._output_path, self._streamlink_options, plugins)

    def start_recorder(self, username: str, recorder: TwitchRecorder):
        recorder.startRecording(self._streams[username.lower()])