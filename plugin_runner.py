from threading import Thread
import logging

log = logging.getLogger(__file__)

class PluginRunner(Thread):
    def __init__(self, plugins, method, params):
        super().__init__()

        self._plugins = plugins
        self._method_name = method
        self._params = params

    def run(self):
        for p in self._plugins:
            try:
                getattr(p, self._method_name)(*self._params)
            except Exception as e:
                log.error(f"Error in plugin {p.__class__.get_name()}: {repr(e)}")
