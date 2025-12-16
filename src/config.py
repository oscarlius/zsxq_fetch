import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
AUTH_FILE_PATH = BASE_DIR / os.getenv("ZSXQ_AUTH_FILE", "auth.json")

# Ensure download dir exists
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Feishu Config
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_BITABLE_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN")
FEISHU_TABLE_ID = os.getenv("FEISHU_TABLE_ID")

# Validation
if not all([FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BITABLE_APP_TOKEN, FEISHU_TABLE_ID]):
    logger.warning("Feishu configuration is incomplete in .env file.")

# Logger Configuration
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(BASE_DIR / "logs" / "crawler.log", rotation="10 MB", level="DEBUG")
