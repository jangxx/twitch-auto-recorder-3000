from typing import Optional
import requests

from .plugin_base import Plugin, StreamMetadata
from pydantic import BaseModel

class PushoverPluginConfig(BaseModel):
    user_key: str
    api_token: str

class PushoverPlugin(Plugin):
    def __init__(self, config: PushoverPluginConfig):
        super().__init__(config)

    @staticmethod
    def create_config(raw_config: dict) -> PushoverPluginConfig:
        return PushoverPluginConfig(**raw_config)

    @staticmethod
    def get_name():
        return "Pushover-Notifications"

    def _send_message(self, message: str):
        requests.post("https://api.pushover.net/1/messages.json", json={
            "token": self._config.api_token,
            "user": self._config.user_key,
            "message": message,
        })

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        if not restart:
            self._send_message(f"Started recording of user {stream_metadata.displayUsername}")
        else:
            self._send_message(f"Restarted recording of user {stream_metadata.displayUsername}")

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path, error=None, finish=True):
        if finish:
            self._send_message(f"Finished recording of user {stream_metadata.displayUsername}")
        elif error is None: # and not finish
            self._send_message(f"Stopped recording of user {stream_metadata.displayUsername}")
        else: # error is not None
            self._send_message(f"Encountered error while recording user {stream_metadata.displayUsername}: {repr(error)}")

PluginExport = PushoverPlugin