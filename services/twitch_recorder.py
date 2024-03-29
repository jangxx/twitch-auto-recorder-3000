from threading import Thread, Event
import logging
from datetime import datetime
import os
import sys
import time

import pathvalidate
import streamlink
from streamlink.exceptions import StreamError

from lib.stream_metadata import StreamMetadata
from plugin_runner import PluginRunner
from lib.recorder_base import RecorderBase

log = logging.getLogger(__file__)

class TwitchRecorder(RecorderBase):
    def __init__(self, username: str, quality: str, output_path: str, streamlink_options, plugins):
        super().__init__()
        self._launch_params = (username, quality, output_path, streamlink_options, plugins) # make it easier to create a fresh copy later in case we need one

        self._username = username.lower()
        self._quality = quality
        self._output_path = os.path.join(output_path, username)
        self._streamlink_options = streamlink_options

        self._cloned = False
        
        self._current_title = None
        self._current_metadata: StreamMetadata = None
        self._current_stream = None
        self._recording_path = None

        self._stop_event = Event()

        self._plugins = [p(c) for p,c in plugins]

    def getFreshClone(self):
        new_recorder = TwitchRecorder(*self._launch_params)
        new_recorder._current_title = self._current_title
        new_recorder._current_metadata = self._current_metadata
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
                self._is_initialized = True

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
        self._is_finished = True
        log.info(f"Stopped recording of twitch user {self._username}")
        
        if len(self._plugins) > 0:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, self._recording_path ], { "error": self._encountered_error, "finish": False })
            runner.start()

    def startRecording(self, metadata: StreamMetadata):
        if self._recording:
            return

        log.info(f"Start recording of twitch user {self._username} with quality '{self._quality}'")

        session = streamlink.Streamlink()

        for option in self._streamlink_options:
            session.set_option(option[0], option[1])

        streams = session.streams(f"https://twitch.tv/{self._username}")

        if self._quality not in streams:
            self._stop_time = time.time()
            self._encountered_error = Exception(f"Could not find quality '{self._quality}' in the list of available qualities.")
            log.error(f"Could not find quality '{self._quality}' in the list of available qualities. Options are: {', '.join(streams.keys())}")
            return

        current_stream = streams[self._quality]

        if self._username not in current_stream.to_manifest_url():
            self._stop_time = time.time()
            self._encountered_error = Exception(f"This stream is a hosted stream by a different person and is therefore not going to be recorded.")
            log.error(f"This stream is a hosted stream by a different person and is therefore not going to be recorded.")
            return

        if self._current_title is None: # otherwise we are cloned -> reuse the old title so we can append to the same file
            if "win" in sys.platform:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H_%M_%S')}_{self._username}_{pathvalidate.sanitize_filename(metadata.title)}"
            else:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H:%M:%S')}_{self._username}_{pathvalidate.sanitize_filename(metadata.title)}"

        self._current_metadata = metadata

        self._stop_event.clear()
        self._current_stream = current_stream
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