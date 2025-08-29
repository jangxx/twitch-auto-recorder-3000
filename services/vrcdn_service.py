from datetime import datetime
import logging
from typing import Dict, List
import asyncio
import aiohttp

from lib.config import Config
from lib.stream_metadata import StreamMetadata
from plugins.plugin_base import Plugin
from lib.service_base import ServiceBase
from services.vrcdn_recorder import VRCDNRecorder

log = logging.getLogger(__file__)

async def check_url(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return True
            else:
                return False
    except:
        return False

async def check_urls(urls: Dict[str, str]):
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = { username: asyncio.ensure_future(check_url(session, url)) for username, url in urls.items() }

        await asyncio.gather(*results.values())

        results = { username: result.result() for username, result in results.items() }

    return results

class VRCDNService(ServiceBase):
    def __init__(self):
        super().__init__()

        self._online_users = set()
        self._output_path = None

    def init(self, config: Config):
        self._output_path = config.value("output_path")

        return True
    
    def is_user_live(self, username: str) -> bool:
        return username in self._online_users
    
    def update_streams(self, usernames: List[str]):
        self._online_users = set()

        loop = asyncio.get_event_loop_policy().get_event_loop()
        urls = { username: f"https://stream.vrcdn.live/live/{username}.live.ts" for username in usernames }

        users_live = loop.run_until_complete(check_urls(urls))

        for username, is_live in users_live.items():
            if is_live:
                self._online_users.add(username)

        return len(self._online_users)


    def get_recorder(self, username: str, params: List[str], plugins: List[Plugin]) -> VRCDNRecorder:
        return VRCDNRecorder(username, self._output_path, plugins)
    
    def start_recorder(self, username: str, recorder: VRCDNRecorder):
        metadata = StreamMetadata(
            username=username,
            displayUsername=username,
            title="VRCDN Stream",
            startedAt=datetime.now(),
            service="vrcdn",
            additionalData={},
        )

        recorder.startRecording(metadata)