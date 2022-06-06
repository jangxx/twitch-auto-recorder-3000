from threading import Thread, Event
import logging
from datetime import datetime
import os
import sys
import time

import random

import pathvalidate
import streamlink
from streamlink.exceptions import StreamError

from plugin_runner import PluginRunner

log = logging.getLogger(__file__)

class Recorder(Thread):
    def __init__(self, username, quality, output_path, streamlink_options, plugins):
        super().__init__()
        self._launch_params = (username, quality, output_path, streamlink_options, plugins) # make it easier to create a fresh copy later in case we need one

        self._username = username
        self._quality = quality
        self._output_path = os.path.join(output_path, username)
        self._streamlink_options = streamlink_options

        self._cloned = False
        self._recording = False
        self._encountered_error = None
        self._current_title = None
        self._current_metadata = None
        self._current_stream = None
        self._recording_path = None
        self._stop_time = 0
        self._stop_event = Event()

        self._plugins = [p(c) for p,c in plugins]

    def isRecording(self):
        return self._recording

    def encounteredError(self):
        return self._encountered_error is not None

    def getStopTime(self):
        return self._stop_time

    def getFreshClone(self):
        new_recorder = Recorder(*self._launch_params)
        new_recorder._current_title = self._current_title
        new_recorder._stop_time = self._stop_time
        new_recorder._recording_path = self._recording_path
        new_recorder._cloned = True
        return new_recorder

    def run(self) -> None:
        stream_fd = None

        try:
            if not os.path.exists(self._output_path):
                os.makedirs(self._output_path, exist_ok=True)

            self._recording_path = os.path.join(self._output_path, self._current_title + ".ts")

            with open(self._recording_path, "ab") as output_file:
                stream_fd = self._current_stream.open()

                self._recording = True

                while not self._stop_event.is_set():
                    data = stream_fd.read(1024)

                    if not data: # stream has ended
                        break

                    output_file.write(data)
        except StreamError as e:
            log.error(f"Error while opening stream: {repr(e)}")
            self._encountered_error = e
        except IOError as e:
            log.error(f"Error while writing output file: {repr(e)}")
            self._encountered_error = e
        except Exception as e:
            log.error(f"Error while recording: {repr(e)}")
            self._encountered_error = e
        finally:
            self._stop_time = time.time()

            if stream_fd is not None:
                stream_fd.close()

        self._recording = False
        log.info(f"Stopped recording of twitch user {self._username}")
        
        if len(self._plugins) > 0:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, self._recording_path ], { "error": self._encountered_error, "finish": False })
            runner.start()

    def startRecording(self, metadata):
        if self._recording:
            return

        log.info(f"Start recording of twitch user {self._username} with quality '{self._quality}'")

        session = streamlink.Streamlink()

        for option in self._streamlink_options:
            session.set_option(option[0], option[1])

        streams = session.streams(f"https://twitch.tv/{self._username}")

        if not self._quality in streams:
            self._stop_time = time.time()
            self._encountered_error = Exception(f"Could not find quality '{self._quality}' in the list of available qualities.")
            log.error(f"Could not find quality '{self._quality}' in the list of available qualities. Options are: {', '.join(streams.keys())}")
            return

        if self._current_title is None: # otherwise we are cloned -> reuse the old title so we can append to the same file
            if "win" in sys.platform:
                self._current_title = f"{datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}_{self._username}_{pathvalidate.sanitize_filename(metadata['title'])}"
            else:
                self._current_title = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}_{self._username}_{pathvalidate.sanitize_filename(metadata['title'])}"

        self._current_metadata = metadata

        self._stop_event.clear()
        self._current_stream = streams[self._quality]
        self.start()

        if len(self._plugins) > 0:
            if not self._cloned:
                runner = PluginRunner(self._plugins, "handle_recording_start", [ self._current_metadata ], { "restart": False })
            else:
                runner = PluginRunner(self._plugins, "handle_recording_start", [ self._current_metadata ], { "restart": True })
            runner.start()

    def stopRecording(self):
        self._stop_event.set()

    def finish(self):
        if self._recording_path is not None:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, self._recording_path ], { "error": None, "finish": True })
            runner.start()