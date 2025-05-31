import os

import dotenv

dotenv.load_dotenv()

# configure these in the `.env` file
BOT_TOKEN = os.environ["BOT_TOKEN"]
DOMAIN = os.environ["DOMAIN"]
MAP_DL_MIRROR = os.environ["MAP_DL_MIRROR"]

API_URL = f"https://osu.{DOMAIN}/api"
OLD_API_URL = f"https://api.{DOMAIN}"
API_STRFTIME = "%Y-%m-%dT%H:%M:%S"
