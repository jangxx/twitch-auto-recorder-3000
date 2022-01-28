class Plugin:
    def __init__(self, config):
        self._config = config

    @staticmethod
    def get_name():
        return "Unnamed-Plugin"

    def handle_recording_start(self, stream_metadata, restart=False):
        pass # abstact method

    def handle_recording_end(self, stream_metadata, output_path, error=None, finish=True):
        pass # abstract method
