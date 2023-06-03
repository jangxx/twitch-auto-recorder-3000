from dataclasses import dataclass
from datetime import datetime

@dataclass
class StreamMetadata:
    username: str
    displayUsername: str
    title: str
    startedAt: datetime

    service: str
    additionalData: dict