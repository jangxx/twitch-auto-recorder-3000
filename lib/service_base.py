from abc import ABC, abstractmethod
from typing import Iterable, List

from lib.config import Config
from plugins.plugin_base import Plugin
from lib.recorder_base import RecorderBase

class ServiceBase[R](ABC):
    def __init__(self):
        self.initialized = False
    
    @abstractmethod
    def init(self, config: Config) -> bool:
        pass

    @abstractmethod
    def is_user_live(self, username: str) -> bool:
        pass
    
    # returns the number of active/live streams
    @abstractmethod
    def update_streams(self, usernames: Iterable[str]) -> int:
        pass

    @abstractmethod
    def get_recorder(self, username: str, params: List[str], plugins: list[tuple[type[Plugin], dict]]) -> R:
        pass

    @abstractmethod
    def start_recorder(self, username: str, recorder: R):
        pass