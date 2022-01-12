class Plugin:
    def __init__(self, config):
        self._config = config

    @staticmethod
    def get_name():
        return "Unnamed-Plugin"

    def handle_recording_start(self, stream_metadata):
        pass

    def handle_recording_restart(self, stream_metadata):
        pass

    def handle_recording_end(self, stream_metadata, output_path):
        pass

    def handle_recording_error(self, stream_metadata, output_path, error):
        pass