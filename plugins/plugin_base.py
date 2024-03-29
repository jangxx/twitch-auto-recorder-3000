from lib.stream_metadata import StreamMetadata

class Plugin:
    def __init__(self, config):
        self._config = config

    @staticmethod
    def get_name():
        return "Unnamed-Plugin"

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        pass # abstract but optional to implement

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path: str, error=None, finish=True):
        pass # abstract but optional to implement

class PluginException(Exception):
    pass