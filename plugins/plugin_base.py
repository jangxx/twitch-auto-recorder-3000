from typing import Optional
from lib.stream_metadata import StreamMetadata

class Plugin[C]:
    _config: C

    def __init__(self, config: C):
        self._config = config

    @staticmethod
    def create_config(raw_config: dict) -> Optional[C]:
        return None # abstract but optional to implement

    @staticmethod
    def get_name() -> str:
        return "Unnamed-Plugin"

    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        pass # abstract but optional to implement

    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path: str, error=None, finish=True):
        pass # abstract but optional to implement

class PluginException(Exception):
    pass