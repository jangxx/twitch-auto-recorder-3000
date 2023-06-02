import logging
from typing import Dict, List
import asyncio

import aiohttp

from config import Config
from plugins.plugin_base import Plugin
from lib.service_base import ServiceBase
from services.vrcdn_recorder import VRCDNRecorder

log = logging.getLogger(__file__)

async def check_url(session: aiohttp.ClientSession, url: str):
    print("check", url)

    try:
        async with session.get(url) as resp:
            print(resp.status)

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

        self._streams = {}

        self._output_path = None


    def init(self, config: Config):
        self._output_path = config.value("output_path")

        return True
    
    def is_user_live(self, username: str) -> bool:
        return username in self._streams
    
    def update_streams(self, usernames: List[str]):
        self._streams = {}

        loop = asyncio.get_event_loop()
        urls = { username: f"https://stream.vrcdn.live/live/{username}.live.ts" for username in usernames }

        result = loop.run_until_complete(check_urls(urls))

        print(result)

        return 0

    def get_recorder(self, username: str, params: List[str], plugins: List[Plugin]) -> VRCDNRecorder:
        return None
    
    def start_recorder(self, username: str, recorder: VRCDNRecorder):
        recorder.startRecording( self._streams[username.lower()] )