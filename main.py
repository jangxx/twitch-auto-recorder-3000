import argparse
import time
import os
import logging
import re
import importlib

from twitchAPI.twitch import Twitch

from watch import Watch

def streamlink_option_type(val):
    optionRe = re.compile("^(.*?):(.*?)=(.*)$")
    matches = optionRe.match(val)

    if matches is None:
        raise argparse.ArgumentError(f"Streamlink option parameter '{val}' could not be parsed")

    contructors = {
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
    }

    if not matches.group(2) in contructors:
        raise argparse.ArgumentError(f"Streamlink option parameter '{val}' specifies an invalid type. Possible types are {', '.join(contructors.keys())}")

    return matches.group(1), contructors[matches.group(2)](matches.group(3))

parser = argparse.ArgumentParser(description="A tool to automatically download streams from twitch as streamers go live")
parser.add_argument("--twitch-clientid", metavar="clientid", dest="clientid", help="Client ID of your twitch application", required=True)
parser.add_argument("--twitch-secret", metavar="secret", dest="secret", help="Client Secret of your twitch application", required=True)
parser.add_argument("-O", "--output-path", metavar="path", dest="output_path", help="Path where the recordings are stored (Default: ./recordings)", default="./recordings")
parser.add_argument("-s", metavar="username", dest="watched_accounts", help="Add a username to the list of watched streamers. The quality can be set by writing it behind the username separated by a colon ('username:quality')", action="append", required=True)
parser.add_argument("--update-interval", metavar="seconds", dest="update_interval", help="Update interval in seconds (Default: 120)", type=int, default=300)
parser.add_argument("--log", metavar="loglevel", dest="loglevel", help="Sets the loglevel, one of CRITICAL, ERROR, WARNING, INFO, DEBUG (Default: INFO)", default="INFO")
parser.add_argument("-c", metavar="option", dest="streamlink_options", help="Set a streamlink config option in the format optionname:type=value, e.g. '-c ipv4:bool=True' or '-c ffmpeg-ffmpeg:str=/usr/bin/ffmpeg'", action="append", default=[], type=streamlink_option_type)
parser.add_argument("-p", metavar="plugin", dest="plugins", help="Enable a plugin", default=[], action="append")

args = parser.parse_args()
twitch = Twitch(args.clientid, args.secret)

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


if __name__ == "__main__":
    if not os.path.exists(args.output_path):
        log.info(f"Output path {args.output_path} doesn't exist, creating it now...")
        os.makedirs(args.output_path, exist_ok=True)

    plugins = [
        importlib.import_module(f"plugins.{p}").PluginExport for p in args.plugins
    ]

    for p in plugins:
        log.info(f"Loaded plugin {p.get_name()}")

    log.info(f"Checking twitch every {args.update_interval} seconds")

    watches = {}
    for username_definition in args.watched_accounts:
        username_definition = username_definition.split(":")

        if len(username_definition) == 1:
            username_definition.append("best") # default quality is best

        [ username, quality ] = username_definition

        watches[username] = Watch(username, quality, args.output_path, args.streamlink_options, plugins)
        log.info(f"Watching twitch user {username}")

    # print(watches)

    try:
        while True:
            streams = None
            try:
                streams = get_all_streams(watches.keys())
            except Exception as ex:
                log.error(f"Error while fetching streams: {repr(ex)}")

            if streams is not None:
                # check if the status of any of our watches has changed
                for username,watch in watches.items():
                    is_live = (username in streams and streams[username]["type"] == "live")

                    if is_live and not watch.isRecording():
                        watch.startRecording(streams[username])

            time.sleep(args.update_interval)
    except KeyboardInterrupt:
        pass

    for watch in watches.values():
        if watch.isRecording():
            watch.stopRecording()