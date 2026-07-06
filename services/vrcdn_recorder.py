from threading import Event, Thread
import logging
import os
import sys
import time
from typing import Optional
import tempfile

import requests
import ffmpeg # type: ignore

from lib.stream_metadata import StreamMetadata
from lib.plugin_runner import PluginRunner
from lib.recorder_base import RecorderBase
from plugins.plugin_base import Plugin

log = logging.getLogger(__file__)

class VRCDNRecorder(RecorderBase):
    _username: str
    _output_path: str

    _cloned_paths: list[str] = []

    _current_title: Optional[str]
    _current_title_suffix: Optional[str]
    _current_metadata: Optional[StreamMetadata]
    _recording_path: Optional[str]

    _plugins: list[Plugin]

    def __init__(self, username: str, output_path: str, plugins: list[tuple[type[Plugin], dict]]):
        super().__init__()
        self.daemon = True

        self._launch_params = (username, output_path, plugins)

        self._username = username
        self._output_path = os.path.join(output_path, "vrcdn_" + username)

        self._cloned_paths = []

        self._current_title = None
        self._current_title_suffix = None
        self._current_metadata: Optional[StreamMetadata] = None
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
        new_recorder._cloned_paths = list(self._cloned_paths)

        if self._recording_path is not None:
            new_recorder._cloned_paths.append(self._recording_path)

        return new_recorder
    
    def run(self) -> None:
        if self._current_title is None:
            raise Exception("Cannot run recorder without having set a title first")

        resp = None

        recording_url = f"https://stream.vrcdn.live/live/{self._username}.live.ts"
        ever_started = False

        try:
            if not os.path.exists(self._output_path):
                os.makedirs(self._output_path, exist_ok=True)

            current_title = self._current_title

            if self._current_title_suffix is not None:
                current_title += self._current_title_suffix

            self._recording_path = os.path.join(self._output_path, current_title + ".ts")

            with open(self._recording_path, "wb") as output_file:
                resp = requests.get(recording_url, stream=True, timeout=10)
                resp.raise_for_status()
                stream_iterator = resp.iter_content(chunk_size=1024*10)

                self._recording = True
                self._is_initialized = True
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
            self._is_initialized = True # just in case we encounter an error earlier
            self._stop_time = time.time()

            if resp is not None:
                resp.close()

        # if a file was written, remux it into an mp4 file to normalize video/audio stream order
        if self._recording_path is not None and os.path.exists(self._recording_path):
            if os.path.getsize(self._recording_path) == 0:
                os.unlink(self._recording_path)
                self._recording_path = None
            else:
                remuxed_path = self._recording_path + ".mp4"

                try:
                    ffmpeg.input(self._recording_path).output(remuxed_path, codec="copy").run()

                    # delete the old unremuxed file after ffmpeg finished without throwing
                    os.unlink(self._recording_path)

                    self._recording_path = remuxed_path
                except Exception as e:
                    log.error(f"Error while remuxing: {repr(e)}")

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

        if self._current_title is None: # otherwise we are cloned -> reuse the old title so we can append the cloned suffix
            if "win" in sys.platform:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H_%M_%S')}_{self._username}"
            else:
                self._current_title = f"{metadata.startedAt.strftime('%Y-%m-%d_%H:%M:%S')}_{self._username}"

        self._current_title_suffix = f"_{len(self._cloned_paths)}"

        self._current_metadata = metadata

        self._stop_event.clear()
        self._start_event.clear()
        self.start()

        if len(self._plugins) > 0:
            if len(self._cloned_paths) == 0:
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
        if (self._recording_path is not None or len(self._cloned_paths) > 0) and self._current_title is not None:
            current_title = self._current_title

            # this "concatenation" needs to run even if there is only a single file, otherwise the final output file is not a .ts file
            def concat_file_thread():
                # concat all the files together with ffmpeg before passing it to plugin
                concat_error = None

                with tempfile.NamedTemporaryFile(mode="w", delete_on_close=False) as list_file:
                    concatenated_files = self._cloned_paths

                    if self._recording_path is not None:
                        concatenated_files.append(self._recording_path)

                    for cf in concatenated_files:
                        list_file.write(f"file '{os.path.abspath(cf)}'\n")

                    recording_path = os.path.join(self._output_path, current_title + ".ts")

                    list_file.flush()
                    list_file.close()

                    try:
                        ffmpeg.input(list_file.name, format="concat", safe=0).output(recording_path, codec="copy").run()

                        for cf in concatenated_files:
                            os.unlink(cf)
                    except Exception as e:
                        log.error(f"Error while concatenating segments: {repr(e)}")
                        concat_error = e

                # run the plugin runner in the same concat thread
                runner = PluginRunner(self._plugins, "handle_recording_end", [ self._current_metadata, recording_path ], { "error": concat_error, "finish": True })
                runner.run()

            concat_thread = Thread(target=concat_file_thread)
            concat_thread.start()