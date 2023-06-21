REQUIRED_CONFIG = [
    ("streamers",),
]

def merge_config_dicts(base_config, merge_src):
    result = {}
    for key in merge_src:
        if key in base_config:
            if isinstance(base_config[key], dict) and isinstance(merge_src[key], dict):
                result[key] = merge_config_dicts(base_config[key], merge_src[key])
            elif not isinstance(base_config[key], dict) and not isinstance(merge_src[key], dict):
                if isinstance(base_config[key], list) and isinstance(merge_src[key], list):
                    result[key] = base_config[key] + merge_src[key]
                elif merge_src[key] is not None:
                    result[key] = merge_src[key]
            else: # objects are of different types (one is dict, the other isn't)
                result[key] = base_config[key] # just use the base config in that case
        elif merge_src[key] is not None:
            result[key] = merge_src[key]

    for key in base_config:
        if key not in result:
            result[key] = base_config[key]

    return result

class Config:
    def __init__(self):
        self._config = {
            "twitch": {
                "clientid": None,
                "secret": None,
            },
            "output_path": "./recordings",
            "streamers": [],
            "update_interval": 120,
            "update_end_interval": 10,
            "stream_end_timeout": 0,
            "streamlink_options": [],
            "plugins": {},
        }

    def find_missing_keys(self):
        for config_path in REQUIRED_CONFIG:
            obj = self._config

            for step in config_path:
                obj = obj[ step ]

                if obj is None or (isinstance(obj, list) and len(obj) == 0):
                    return config_path

        return None

    def is_valid(self):
        return self.find_missing_keys() is None

    def value(self, path):
        ret = self._config

        if type(path) is not list:
            path = [ path ]

        for e in path:
            ret = ret[e]

        return ret

    def merge(self, other_config):
        self._config = merge_config_dicts(self._config, other_config)
