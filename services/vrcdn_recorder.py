from threading import Thread, Event
import logging
from datetime import datetime
import os
import sys
import time

import pathvalidate
import requests

from lib.stream_metadata import StreamMetadata
from plugin_runner import PluginRunner
from lib.recorder_base import RecorderBase

log = logging.getLogger(__file__)

class VRCDNRecorder(RecorderBase):
    def __init__(self, username: str, output_path: str, plugins):
        super().__init__()
        self.daemon = True

        self._launch_params = (username, output_path, plugins)

        self._username = username
        self._output_path = os.path.join(output_path, "vrcdn_" + username)

        self._cloned = False

        self._current_title = None
        self._current_metadata: StreamMetadata = None
        self._recording_path = None

        self._stop_event = Event()
        self._start_event = Event()

        self._plugins = [p(c) for p,c in plugins]

    def getFreshClone(self):
        new_recorder = VRCDNRecorder(*self._launch_params)
        new_recorder._current_title = self._current_title
        new_recorder._current_metadata = self._current_metadata
        new_recorder._stop_time = self._stop_time
        new_recorder._recording_path = self._recording_path
        new_recorder._cloned = True
        return new_recorder
    
    def run(self) -> None:
        resp = None

        recording_url = f"https://stream.vrcdn.live/live/{self._username}.live.ts"
        ever_started = False

        try:
            if not os.path.exists(self._output_path):
                os.makedirs(self._output_path, exist_ok=True)

            self._recording_path = os.path.join(self._output_path, self._current_title + ".ts")

            with open(self._recording_path, "ab") as output_file:
                resp = requests.get(recording_url, stream=True, timeout=5)
                resp.raise_for_status()
                stream_iterator = resp.iter_content(None)

                self._recording = True
                ever_started = True
                self._start_event.set()

                while not self._stop_event.is_set():
                    data = next(stream_iterator)

                    output_file.write(data)
        except StopIteration:
            pass
        except requests.HTTPError as e:
            log.error(f"Error while opening stream: {repr(e)}")
            self._encountered_error = e
        except IOError as e:
            log.error(f"Error while starting recording: {repr(e)}")
            self._encountered_error = e
        except Exception as e:
            log.error(f"Error while recording: {repr(e)}")
            self._encountered_error = e
        finally:
            self._stop_time = time.time()

            if resp is not None:
                resp.close()

        self._recording = False
        self._is_finished = True
        log.info(f"Stopped recording of VRCDN user {self._username}")
        
        if not ever_started: # tell the main thread that we are done already
            self._start_event.set()

        if len(self._plugins) > 0:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, self._recording_path ], { "error": self._encountered_error, "finish": False })
            runner.start()

    def startRecording(self, metadata: StreamMetadata):
        if self._recording:
            return

        log.info(f"Start recording of VRCDN user {self._username}")

        if self._current_title is None: # otherwise we are cloned -> reuse the old title so we can append to the same file
            if "win" in sys.platform:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H_%M_%S')}_{self._username}"
            else:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H:%M:%S')}_{self._username}"

        self._current_metadata = metadata

        self._stop_event.clear()
        self._start_event.clear()
        self.start()

        if len(self._plugins) > 0:
            if not self._cloned:
                runner = PluginRunner(self._plugins, "handle_recording_start", [ self._current_metadata ], { "restart": False })
            else:
                runner = PluginRunner(self._plugins, "handle_recording_start", [ self._current_metadata ], { "restart": True })
            runner.start()
        
        # wait until the thread has actually started recording or failed
        self._start_event.wait(20) # 20 sec timeout so we can't lock up completely

    def stopRecording(self):
        self._stop_event.set()

    def finish(self):
        log.info(f"Finished recording of VRCDN user {self._username}")
        if self._recording_path is not None:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, self._recording_path ], { "error": None, "finish": True })
            runner.start()