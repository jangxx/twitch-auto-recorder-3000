from .plugin_base import Plugin

import pushover

class PushoverPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)

        self._client = pushover.Client(self._config["user_key"], api_token=self._config["api_token"])

    @staticmethod
    def get_name():
        return "Pushover-Notifications"

    def handle_recording_start(self, stream_metadata, restart=False):
        if not restart:
            self._client.send_message(f"Started recording of user {stream_metadata['user_name']}")
        else:
            self._client.send_message(f"Restarted recording of user {stream_metadata['user_name']}")

    def handle_recording_end(self, stream_metadata, output_path, error=None, finish=True):
        if finish:
            self._client.send_message(f"Finished recording of user {stream_metadata['user_name']}")
        elif error is None: # and not finish
            self._client.send_message(f"Stopped recording of user {stream_metadata['user_name']}")
        else: # error is not None
            self._client.send_message(f"Encountered error while recording user {stream_metadata['user_name']}: {repr(error)}")

PluginExport = PushoverPlugin