from .plugin_base import Plugin, StreamMetadata

import pushover

class PushoverPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)

        self._client = pushover.Client(self._config["user_key"], api_token=self._config["api_token"])

    @staticmethod
    def get_name():
        return "Pushover-Notifications"

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        if not restart:
            self._client.send_message(f"Started recording of user {stream_metadata.displayUsername}")
        else:
            self._client.send_message(f"Restarted recording of user {stream_metadata.displayUsername}")

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path, error=None, finish=True):
        if finish:
            self._client.send_message(f"Finished recording of user {stream_metadata.displayUsername}")
        elif error is None: # and not finish
            self._client.send_message(f"Stopped recording of user {stream_metadata.displayUsername}")
        else: # error is not None
            self._client.send_message(f"Encountered error while recording user {stream_metadata.displayUsername}: {repr(error)}")

PluginExport = PushoverPlugin