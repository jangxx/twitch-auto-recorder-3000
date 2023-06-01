from dataclasses import dataclass
from typing import List

@dataclass
class UsernameDefinition:
    service: str
    username: str
    parameters: List[str]

    def get_id(self):
        return f"{self.service}={self.username}"