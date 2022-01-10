class Plugin:
    def __init__(self, config):
        self._config = config

    @staticmethod
    def get_name():
        return "Unnamed-Plugin"

    def process_recording(self, output_path, stream_metadata):
        pass