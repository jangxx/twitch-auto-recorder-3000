from .plugin_base import Plugin, PluginException, StreamMetadata

import requests

def send_notification(webhook, message):
    try:
        requests.post(webhook, json={
            "content": message,
        })
    except Exception as ex:
        print("Sending discord notification failed with an exception: " + repr(ex))

class DiscordNotificationPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)

        if "webhook" not in self._config:
            raise PluginException("Config key 'webhook' is missing")

    @staticmethod
    def get_name():
        return "Discord-Notifications"

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        if not restart:
            send_notification(self._config["webhook"], f"Started recording of user {stream_metadata.displayUsername}")
        else:
            send_notification(self._config["webhook"], f"Restarted recording of user {stream_metadata.displayUsername}")

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path, error=None, finish=True):
        if finish:
            send_notification(self._config["webhook"], f"Finished recording of user {stream_metadata.displayUsername}")
        elif error is None: # and not finish
            send_notification(self._config["webhook"], f"Stopped recording of user {stream_metadata.displayUsername}")
        else: # error is not None
            send_notification(self._config["webhook"], f"Encountered error while recording user {stream_metadata.displayUsername}: {repr(error)}")

PluginExport = DiscordNotificationPlugin