from abc import ABC, abstractmethod
from lib.stream_metadata import StreamMetadata

class Plugin(ABC):
    def __init__(self, config):
        self._config = config

    @staticmethod
    def get_name():
        return "Unnamed-Plugin"

    @abstractmethod
    def handle_recording_start(self, stream_metadata: StreamMetadata, restart=False):
        pass

    @abstractmethod
    def handle_recording_end(self, stream_metadata: StreamMetadata, output_path: str, error=None, finish=True):
        pass

class PluginException(Exception):
    pass