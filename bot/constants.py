import os

# configure these in the `.env` file
DOMAIN = os.environ["DOMAIN"]
MAP_DL_MIRROR = os.environ["MAP_DL_MIRROR"]

NEW_API_URL = f"https://osu.{DOMAIN}/api"
OLD_API_URL = f"https://api.{DOMAIN}"
API_STRFTIME = "%Y-%m-%dT%H:%M:%S"
