from threading import Thread, Event
import logging
from datetime import datetime
import os
import pathvalidate

import streamlink
from streamlink.exceptions import StreamError

from plugin_runner import PluginRunner

log = logging.getLogger(__file__)

class Watch(Thread):
    def __init__(self, username, quality, output_path, streamlink_options, plugins):
        super().__init__()
        self._username = username
        self._quality = quality
        self._output_path = os.path.join(output_path, username)
        self._streamlink_options = streamlink_options

        self._recording = False
        self._current_title = ""
        self._current_metadata = None
        self._current_stream = None
        self._stop_event = Event()

        self._plugins = [p(c) for p,c in plugins]

    def isRecording(self):
        return self._recording

    def run(self) -> None:
        try:
            if not os.path.exists(self._output_path):
                os.makedirs(self._output_path, exist_ok=True)

            recording_path = os.path.join(self._output_path, self._current_title + ".ts")

            with open(recording_path, "ab") as output_file:
                stream_fd = self._current_stream.open()

                self._recording = True

                while not self._stop_event.is_set():
                    data = stream_fd.read(1024)

                    if not data: # stream has ended
                        break

                    output_file.write(data)

                output_file.close()
                stream_fd.close()
        except StreamError as e:
            log.error(f"Error while opening stream: {repr(e)}")
        except IOError as e:
            log.error(f"Error while writing output file: {repr(e)}")
        except Exception as e:
            log.error(f"Error while recording: {repr(e)}")
        finally:
            self._recording = False
            log.info(f"Stopped recording of twitch user {self._username}")
        
        if len(self._plugins) > 0:
            runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, recording_path ])
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
            log.error(f"Could not find quality '{self._quality}' in the list of available qualities. Options are: {', '.join(streams.keys())}")
            return

        self._current_title = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_{self._username}_{pathvalidate.sanitize_filename(metadata['title'])}"
        self._current_metadata = metadata

        self._stop_event.clear()
        self._current_stream = streams[self._quality]
        self.start()

        if len(self._plugins) > 0:
            runner = PluginRunner(self._plugins, "handle_recording_start", [ self._current_metadata ])
            runner.start()

    def stopRecording(self):
        self._stop_event.set()