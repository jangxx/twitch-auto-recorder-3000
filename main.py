import argparse

parser = argparse.ArgumentParser(description="A tool to automatically download streams from twitch as streamers go live")
parser.add_argument("--twitch-clientid", metavar="clientid", dest="clientid", help="Client ID of your twitch application", required=True)
parser.add_argument("--twitch-secret", metavar="secret", dest="secret", help="Client Secret of your twitch application", required=True)
parser.add_argument("-O", "--output-path", metavar="path", dest="output_path", help="Path where the recordings are stored (Default: ./recordings)", default="./recordings")
parser.add_argument("-s", metavar="username", dest="watched_accounts", help="Add a username to the list of watched streamers", action="append", required=True)

args = parser.parse_args()

print(args)