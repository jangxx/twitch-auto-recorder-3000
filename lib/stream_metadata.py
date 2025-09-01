from dataclasses import dataclass
from datetime import datetime

from twitchAPI.object.api import Stream

@dataclass
class StreamMetadata:
    username: str
    displayUsername: str
    title: str
    startedAt: datetime

    service: str
    additionalData: dict