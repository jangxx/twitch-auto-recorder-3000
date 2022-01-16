import re

from .plugin_base import Plugin

import ffmpeg

class FFmpegRemuxPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)

    @staticmethod
    def get_name():
        return "FFmpeg-Remux"

    def handle_recording_end(self, stream_metadata, output_path, error=None, finish=True):
        if error is None and finish:
            mp4_filename = re.sub("\.ts", ".mp4", output_path)

            ffmpeg.input(output_path).output(mp4_filename, codec="copy", movflags="faststart").run()

PluginExport = FFmpegRemuxPlugin