import requests
from pydantic import BaseModel

from .plugin_base import Plugin, PluginException, StreamMetadata

class DiscordNotificationPluginConfig(BaseModel):
    webhook: str

class DiscordNotificationPlugin(Plugin):
    def __init__(self, config: DiscordNotificationPluginConfig):
        super().__init__(config)

    @staticmethod
    def create_config(raw_config: dict) -> DiscordNotificationPluginConfig:
        return DiscordNotificationPluginConfig(**raw_config)

    @staticmethod
    def get_name():
        return "Discord-Notifications"

    def _send_notification(self, message):
        try:
            requests.post(self._config.webhook, json={
                "content": message,
            })
        except Exception as ex:
            print("Sending discord notification failed with an exception: " + repr(ex))

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        if not restart:
            self._send_notification(f"Started recording of user {stream_metadata.displayUsername}")
        else:
            self._send_notification(f"Restarted recording of user {stream_metadata.displayUsername}")

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path, error=None, finish=True):
        if finish:
            self._send_notification(f"Finished recording of user {stream_metadata.displayUsername}")
        elif error is None: # and not finish
            self._send_notification(f"Stopped recording of user {stream_metadata.displayUsername}")
        else: # error is not None
            self._send_notification(f"Encountered error while recording user {stream_metadata.displayUsername}: {repr(error)}")

PluginExport = DiscordNotificationPlugin