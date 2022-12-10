import argparse
import time
import os
import logging
import re
import importlib
import sys
import json

from twitchAPI.twitch import Twitch
import yaml

from recorder import Recorder
from config import Config

def streamlink_option_type(val):
    option_re = re.compile("^(.*?):(.*?)=(.*)$")
    matches = option_re.match(val)

    if matches is None:
        raise argparse.ArgumentError(f"Streamlink option parameter '{val}' could not be parsed")

    contructors = {
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
    }

    if matches.group(2) not in contructors:
        raise argparse.ArgumentError(f"Streamlink option parameter '{val}' specifies an invalid type. Possible types are {', '.join(contructors.keys())}")

    return matches.group(1), contructors[matches.group(2)](matches.group(3))

parser = argparse.ArgumentParser(description="A tool to automatically download streams from twitch as streamers go live")
parser.add_argument("--twitch-clientid", metavar="clientid", dest="clientid", help="Client ID of your twitch application")
parser.add_argument("--twitch-secret", metavar="secret", dest="secret", help="Client Secret of your twitch application")
parser.add_argument("-O", "--output-path", metavar="path", dest="output_path", help="Path where the recordings are stored (Default: ./recordings)")
parser.add_argument("-s", metavar="username", dest="watched_accounts", help="Add a username to the list of watched streamers. The quality can be set by writing it after the username separated by a colon ('username:quality')", action="append", default=[])
parser.add_argument("--update-interval", metavar="seconds", dest="update_interval", help="Update interval in seconds (Default: 120)", type=int)
parser.add_argument("--stream-end-timeout", metavar="seconds", dest="stream_end_timeout", help="Time to wait after a recording ended before considering the stream as finished (Default: 0)", type=int)
parser.add_argument("--log", metavar="loglevel", dest="loglevel", help="Sets the loglevel, one of CRITICAL, ERROR, WARNING, INFO, DEBUG (Default: INFO)", default="INFO")
parser.add_argument("-c", metavar="option", dest="streamlink_options", help="Set a streamlink config option in the format optionname:type=value, e.g. '-c ipv4:bool=True' or '-c ffmpeg-ffmpeg:str=/usr/bin/ffmpeg'", action="append", default=[], type=streamlink_option_type)
parser.add_argument("-p", metavar="plugin", dest="plugins", help="Enable a plugin", default=[], action="append")
parser.add_argument("-C", "--config", metavar="path", dest="config_file_path", help="Optional path to a config file in YAML format")
parser.add_argument("--print-config", dest="print_config", action="store_true", help="Print the config for debug purposes")

args = parser.parse_args()
config = Config()

# merge config file
if args.config_file_path is not None:
    with open(args.config_file_path, "r") as config_file:
        config_file_content = yaml.load(config_file, yaml.Loader)
    config.merge(dict(config_file_content))

# merge command line options
config.merge({
    "twitch": {
        "clientid": args.clientid,
        "secret": args.secret,
    },
    "streamers": args.watched_accounts,
    "output_path": args.output_path,
    "update_interval": args.update_interval,
    "stream_end_timeout": args.stream_end_timeout,
    "streamlink_options": args.streamlink_options,
    "plugins": { p: {} for p in args.plugins },
})

if args.print_config:
    print(json.dumps(config._config, indent=4))

if not config.is_valid():
    print(f"Incomplete config, missing key: {'.'.join(config.find_missing_keys())}")
    sys.exit(1)

if args.print_config:
    sys.exit(1)

twitch = Twitch( config.value(["twitch", "clientid"]), config.value(["twitch", "secret"]) )

logging.basicConfig(level=args.loglevel, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__file__)

charset_normalizer_logger = logging.getLogger("charset_normalizer")
charset_normalizer_logger.setLevel(logging.CRITICAL)

def get_all_streams(usernames):
    streams = {}
    remaining_usernames = list(usernames)
    cursor = None

    while len(remaining_usernames) > 0:
        resp = twitch.get_streams(
            after=cursor,
            first = 100,
            user_login=remaining_usernames[:100]
        )

        for stream in resp["data"]:
            streams[stream["user_login"]] = stream

        remaining_usernames = remaining_usernames[100:]

    return streams

def recorder_has_error(recorders):
    for recorder in recorders.values():
        if not recorder.isRecording() and recorder.encounteredError():
            return True
    return False

if __name__ == "__main__":
    if not os.path.exists(config.value("output_path")):
        log.info(f"Output path {config.value('output_path')} doesn't exist, creating it now...")
        os.makedirs(config.value("output_path"), exist_ok=True)

    # list of tuples (class, config)
    plugins = [
        (importlib.import_module(f"plugins.{p}").PluginExport, c) for p,c in config.value("plugins").items()
    ]

    for p in plugins:
        log.info(f"Loaded plugin {p[0].get_name()}")

    log.info(f"Checking twitch every {config.value('update_interval')} seconds")

    watches = {}
    for username_definition in config.value("streamers"):
        username_definition = username_definition.split(":")

        if len(username_definition) == 1:
            username_definition.append("best") # default quality is best

        [ username, quality ] = username_definition

        username = username.lower()

        watches[username] = { "quality": quality }
        log.info(f"Watching twitch user {username}")

    recorders = {}
    last_check = 0

    try:
        while True:
            streams = None

            if (time.time() - last_check >= config.value("update_interval") or recorder_has_error(recorders)):
                # if we see an error do another quick check to see if the streamer is still live so we don't miss much
                last_check = time.time()
                try:
                    streams = get_all_streams(watches.keys())
                except Exception as ex:
                    log.error(f"Error while fetching streams: {repr(ex)}")

            if streams is not None:
                # check if the status of any of our watches has changed
                for username,watch in watches.items():
                    is_live = (username in streams and streams[username]["type"] == "live")

                    if username in recorders and not recorders[username].isRecording():
                        stream_end_timeout_reached = (time.time() - recorders[username].getStopTime()) >= config.value("stream_end_timeout")

                        if is_live: # continue recording
                            newRecorder = recorders[username].getFreshClone()
                            recorders[username] = newRecorder
                            recorders[username].startRecording(streams[username])
                        elif stream_end_timeout_reached:
                            recorders[username].finish()
                            del recorders[username] # remove finished recorders

                    if is_live and username not in recorders:
                        recorders[username] = Recorder(username, quality, config.value("output_path"), config.value("streamlink_options"), plugins)
                        recorders[username].startRecording(streams[username])

            time.sleep(1)
    except KeyboardInterrupt:
        pass

    for recorder in recorders.values():
        if recorder.isRecording():
            recorder.stopRecording()