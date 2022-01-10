from threading import Thread
import logging

log = logging.getLogger(__file__)

class PluginRunner(Thread):
    def __init__(self, plugins, output_path, metadata):
        super().__init__()

        self._plugins = plugins
        self._output_path = output_path
        self._metadata = metadata

    def run(self):
        for p in self._plugins:
            try:
                p.process_recording(self._output_path, self._metadata)
            except Exception as e:
                log.error(f"Error in plugin {p.__class__.get_name()} for file {self._output_path}: {repr(e)}")
