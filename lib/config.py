from typing import Optional
from deepmerge.merger import Merger
from pydantic import BaseModel
from pydantic import field_validator

class TwitchConfig(BaseModel):
    clientid: str
    secret: str

class Config(BaseModel):
    twitch: Optional[TwitchConfig]
    output_path: str
    streamers: list[str]
    update_interval: int
    update_end_interval: int
    stream_end_timeout: int
    streamlink_options: list[str]
    plugins: dict[str, dict]

    @field_validator("streamers", mode="after")
    @classmethod
    def validate_streamers(cls, v):
        if len(v) == 0:
            raise ValueError("The 'streamers' field must have at least one entry.")
        return v

ConfigMerger = Merger(
    [
        (list, ["append"]),
        (dict, ["merge"]),
        (set, ["union"]),
    ],
    ["override"],
    ["override_if_not_empty"]
)

DefaultConfigDict = {
    "output_path": "./recordings",
    "streamers": [],
    "update_interval": 120,
    "update_end_interval": 10,
    "stream_end_timeout": 0,
    "streamlink_options": [],
    "plugins": {},
}

def non_empty_dict_or_none(value: dict):
    for v in value.values():
        if v not in (None, {}, []):
            return value
    return None