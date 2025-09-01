import asyncio
from datetime import datetime
import logging
from typing import Iterable, List, Optional

from twitchAPI.twitch import Twitch
from twitchAPI.object.api import Stream

from lib.stream_metadata import StreamMetadata
from lib.config import Config
from plugins.plugin_base import Plugin
from lib.service_base import ServiceBase
from services.twitch_recorder import TwitchRecorder

log = logging.getLogger(__file__)

class TwitchService(ServiceBase[TwitchRecorder]):
    _twitch: Twitch
    _streams: dict[str, Stream]
    _output_path: Optional[str]
    _streamlink_options: list[str]

    def __init__(self):
        super().__init__()

        self._streams = {}

        self._output_path = None
        self._streamlink_options = []

    def init(self, config: Config):
        return asyncio.run(self.init_async(config))

    async def init_async(self, config: Config):
        if config.twitch is None:
            log.info("Twitch API credentials not found, Twitch service is not going to be loaded")
            return False

        self._twitch = await Twitch(
            app_id=config.twitch.clientid,
            app_secret=config.twitch.secret,
        )
        self._output_path = config.output_path
        self._streamlink_options = config.streamlink_options

        return True

    def is_user_live(self, username: str) -> bool:
        return (username in self._streams and self._streams[username].type == "live")
    
    def update_streams(self, usernames: Iterable[str]):
        return asyncio.run(self.update_streams_async(usernames))

    async def update_streams_async(self, usernames: Iterable[str]):
        if not self.initialized:
            return 0

        self._streams = {}
        remaining_usernames = list(u.lower() for u in usernames)
        cursor = None

        while len(remaining_usernames) > 0:
            async for stream in self._twitch.get_streams(
                after=cursor,
                first = 100,
                user_login=remaining_usernames[:100]
            ):
                self._streams[stream.user_login] = stream

            remaining_usernames = remaining_usernames[100:]

        return len(self._streams)

    def get_recorder(self, username: str, params: List[str], plugins: list[tuple[type[Plugin], dict]]) -> TwitchRecorder:
        if self._output_path is None:
            raise Exception("The service has not been initialized yet")

        quality = "best"
        if len(params) > 0:
            quality = params[0]

        return TwitchRecorder(username, quality, self._output_path, self._streamlink_options, plugins)

    def start_recorder(self, username: str, recorder: TwitchRecorder):
        stream_data = self._streams[username.lower()]

        metadata = StreamMetadata(
            username = username,
            displayUsername = stream_data.user_name,
            title = stream_data.title,
            startedAt = datetime.now(), # we could also parse stream_data["started_at"]
            service = "twitch",
            additionalData = stream_data.to_dict(),
        )

        recorder.startRecording(metadata)