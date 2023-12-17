import argparse
import time
import os
import logging
import re
import importlib
import sys
import json
from typing import Dict, List, Type

import yaml
from lib.recorder_base import RecorderBase
from lib.service_base import ServiceBase
from lib.username_definition import UsernameDefinition
from plugins.plugin_base import Plugin

from services.twitch_service import TwitchService
from services.vrcdn_service import VRCDNService
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
parser.add_argument("--update-end-interval", metavar="seconds", dest="update_end_interval", help="Update interval in seconds after a recording has stopped but before it is finished (Default: 10)", type=int)
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
    "update_end_interval": args.update_end_interval,
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
    sys.exit(0)


logging.basicConfig(level=args.loglevel, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__file__)

charset_normalizer_logger = logging.getLogger("charset_normalizer")
charset_normalizer_logger.setLevel(logging.CRITICAL)

services: Dict[str, ServiceBase] = {
    "twitch": TwitchService(),
    "vrcdn": VRCDNService(),
}

# init services
for service in services.values():
    try:
        service.initialized = service.init(config)
    except Exception as e:
        log.error(f"Failed to initialize service {service.get_name()}: {e}")


def recorder_is_finished(recorders: Dict[str, RecorderBase]):
    for recorder in recorders.values():
        if recorder.isFinished():
            return True
    return False

if __name__ == "__main__":
    if not os.path.exists(config.value("output_path")):
        log.info(f"Output path {config.value('output_path')} doesn't exist, creating it now...")
        os.makedirs(config.value("output_path"), exist_ok=True)

    # list of tuples (class, config)
    plugins: List[Type[Plugin]] = [
        (importlib.import_module(f"plugins.{p}").PluginExport, c) for p,c in config.value("plugins").items()
    ]

    for p in plugins:
        log.info(f"Loaded plugin {p[0].get_name()}")

    log.info(f"Checking services every {config.value('update_interval')} seconds")

    username_definition_re = re.compile(r"(?:(\w+)=)?([a-zA-Z0-9_\-]+)((?::\w+)*)")

    watches: Dict[str, UsernameDefinition] = {}
    for streamer_definition in config.value("streamers"):
        username_match = username_definition_re.match(streamer_definition)

        if username_match is None:
            log.error(f"Invalid username definition: {streamer_definition}")
            sys.exit(1)

        username_definition = UsernameDefinition(
            service="twitch",
            username=username_match.group(2),
            parameters=[]
        )

        if username_match.group(1) is not None:
            username_definition.service = username_match.group(1)

        if username_definition.service not in services:
            log.error(f"Invalid service {username_definition.service} for username {username_definition.username}")
            sys.exit(1)

        if not services[username_definition.service].initialized:
            log.error(f"Service {username_definition.service} is not initialized")
            sys.exit(1)

        if username_match.group(3) is not None:
            username_definition.parameters = username_match.group(3).split(":")[1:]

        watches[username_definition.get_id()] = username_definition
        log.info(f"Watching {username_definition.service} user {username_definition.username}")

    recorders: Dict[str, RecorderBase] = {} # mapping from userdef_id to recorder
    last_check = 0

    try:
        while True:
            streams_live = 0

            if (time.time() - last_check >= config.value("update_interval")) or \
               (recorder_is_finished(recorders) and time.time() - last_check >= config.value("update_end_interval")):
                # if there is a stream that just stopped quickly check the live status again
                # -> if there was an error we can quickly restart the stream
                # -> if the finished gracefully we prevent the stream from immediately restarting
                last_check = time.time()

                for service_name, service in services.items():
                    try:
                        streams_live += service.update_streams(w.username for w in watches.values() if w.service == service_name)
                    except Exception as ex:
                        log.error(f"Error while fetching streams for service {service_name}: {repr(ex)}")

            if streams_live > 0 or len(recorders) > 0:
                # check if the status of any of our watches has changed
                for username_id, username_definition in watches.items():
                    is_live = services[username_definition.service].is_user_live(username_definition.username)

                    if username_id in recorders and (recorders[username_id].isInitialized() or recorders[username_id].encounteredError()) and not recorders[username_id].isRecording():
                        stream_end_timeout_reached = (time.time() - recorders[username_id].getStopTime()) >= config.value("stream_end_timeout")

                        if is_live: # continue recording
                            newRecorder = recorders[username_id].getFreshClone()
                            recorders[username_id] = newRecorder
                            services[username_definition.service].start_recorder(username_definition.username, newRecorder)
                        elif stream_end_timeout_reached:
                            recorders[username_id].finish()
                            del recorders[username_id] # remove finished recorders

                    if is_live and username_id not in recorders:
                        recorders[username_id] = services[username_definition.service].get_recorder(username_definition.username, username_definition.parameters, plugins)
                        services[username_definition.service].start_recorder(username_definition.username, recorders[username_id])

            time.sleep(1)
    except KeyboardInterrupt:
        pass

    for recorder in recorders.values():
        if recorder.isRecording():
            recorder.stopRecording()