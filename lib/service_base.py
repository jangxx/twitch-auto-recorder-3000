from abc import ABC, abstractmethod
from typing import List

from config import Config
from plugins.plugin_base import Plugin
from lib.recorder_base import RecorderBase
from lib.username_definition import UsernameDefinition

class ServiceBase(ABC):
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
    def update_streams(self, usernames: List[str]) -> int:
        pass

    @abstractmethod
    def get_recorder(self, username: str, params: List[str], plugins: List[Plugin]) -> RecorderBase:
        pass

    @abstractmethod
    def start_recorder(self, username: str, recorder: RecorderBase):
        pass