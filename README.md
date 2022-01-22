# Twitch Auto Recorder 3000
A better way to automatically download streams from twitch as streamers go live

# Requirements

- Python >=3.7
- `ffmpeg` _if you want to use the ffmpeg plugin_

# Installation

Clone this repositoy and create a new virtualenv in its directory.

    python3 -m venv venv

Activate the virtalenv

_Linux, macOS_:

    source venv/bin/activate

_Windows_:

- Bash: `source venv/Scripts/activate`
- Powershell: `.\venv\Scripts\activate`
- CMD: `.\venv\Scripts\activate.bat`

and then install the required packages:

    pip install -r requirements.txt

if you want to use the plugins, you also have to install their requirements as well:

    pip install -r requirements-plugins.txt

# Usage

Run `python main.py` with some of these command line arguments:

`-h, --help`  
Show help message and exit.

`--twitch-clientid <clientid>`  
**Required:** Client ID of your twitch application (from the [Developer console](https://dev.twitch.tv/console/apps))

`--twitch-secret <secret>`  
**Required:** Client Secret of your twitch application (from the [Developer console](https://dev.twitch.tv/console/apps))

`-s <username>`  
**Required:** Add a username to the list of watched streamers. The quality can be set by writing it after the username separated by a colon ('username:quality')

`-C <path>, --config <path>`  
**Optional:** Path to a config file in YAML format.

`-O <path>, --output-path <path>`  
**Optional:** Path where the recordings are stored (Default: ./recordings)

`--update-interval <seconds>`  
**Optional:** Update interval in seconds (Default: 120)

`--log <loglevel>`  
**Optional:** Sets the loglevel, one of CRITICAL, ERROR, WARNING, INFO, DEBUG (Default: INFO)

`-c <option:type=value>`  
**Advanced:** Set a streamlink config option in the format `optionname:type=value`, e.g. `-c ipv4:bool=True` or `-c ffmpeg-ffmpeg:str=/usr/bin/ffmpeg`
  
`--print-config`  
Print the config for debug purposes, to figure out if it got merged correctly.

Instead of supplying these values as command line arguments, you can also write a config file that contains all (or some) of them.
Options from the config file and the command line will be merged, with command line arguments taking precedence, so you can mix and match.

The config file uses this format:

```yaml
twitch:
    clientid: <clientid>
    secret: <secret>
streamers:
    - <username1>
    - <username2>
streamlink_options:
    - <option1>
    - <option2>
plugins:
    plugin_name:
        option1: <value>
        option2: <value>
    # some plugins don't have configuration 
    # and just need an empty object here to be included
    plugin2_name: {} 
output_path: <path>
update_interval: <interval>
```

Except for the plugin options, all configuration options can be set with command line arguments as well.

# Plugins

Plugins can add some additional postprocessing to your recordings. Two plugins are included in the _plugins/_ directory, which serve as the examples on how to write your own.

`ffmpeg_remux`  
Automatically remuxes the recorded .ts file into a .mp4 (with qtfaststart for better streamability).
It has no config options, so it can be enabled with `-p ffmpeg_remux` or by adding `ffmpeg_remux: {}` to the plugin section of the config file.  
_Note:_ For convenience there is also a clean-up script included in this project _cleanup_remuxed.py_, which takes the recording path as a parameter and which can be run as a cronjob to automatically and periodically delete the already remuxed .ts files.

`pushover`  
This plugin uses [pushover](https://pushover.net) to send notifications about your recordings to your phone. Since it needs configuration, it can only be enabled with the config file:
```yaml
plugins:
    pushover:
        user_key: <user_key>
        api_token: <api_token>
```
You get your user key and an API token on the pushover website.