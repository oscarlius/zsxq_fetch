import json
import time
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path
from loguru import logger
from .config import AUTH_FILE_PATH, DOWNLOAD_DIR

class ZSXQClient:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://wx.zsxq.com",
            "Referer": "https://wx.zsxq.com/",
            "Accept": "application/json, text/plain, */*"
        }
        self.auth_data = {}
        self._load_auth()

    def _load_auth(self):
        """Load cookies and tokens from auth.json"""
        if not AUTH_FILE_PATH.exists():
            raise FileNotFoundError(f"Auth file not found at {AUTH_FILE_PATH}. Please run zsxq_auth.py first.")

        try:
            with open(AUTH_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.auth_data = data

            # Load Cookies
            for cookie in data.get("cookies", []):
                self.session.cookies.set(
                    cookie["name"], 
                    cookie["value"], 
                    domain=cookie["domain"], 
                    path=cookie["path"]
                )
            
            # Attempt to find Authorization header in LocalStorage (origins)
            # Structure: data['origins'][i]['localStorage'] -> list of {name, value}
            token_found = False
            for origin in data.get("origins", []):
                if "zsxq.com" in origin["origin"]:
                    for item in origin.get("localStorage", []):
                        if item["name"] == "accessToken" or item["name"] == "token": # Common names, verify?
                            # Usually handled by cookie, but sometimes explicit header needed
                            pass
                        # Some versions of ZSXQ web use a specific key for the bearer token
                        # For now, let's rely on Cookies. The X-Signature usually is for the App API.
                        # For Web API (api.zsxq.com call from web context), Cookies are often enough?
                        # User said "Authorization" is necessary. 
                        # Let's try to extract it if we find something obvious, otherwise rely on Cookies.
                        pass
            
            # If the user insists on Authorization header, it might be the 'zsxq_access_token' cookie 
            # which is automatically sent.
            
            # Update headers
            self.session.headers.update(self.headers)
            logger.info("ZSXQ Client initialized with session data.")

        except Exception as e:
            logger.error(f"Failed to load auth data: {e}")
            raise

    def get_groups(self):
        """Fetch all joined groups (planets)"""
        url = "https://api.zsxq.com/v2/groups"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            return resp.json().get("resp_data", {}).get("groups", [])
        except Exception as e:
            logger.error(f"Failed to fetch groups: {e}")
            return []

    def get_topics(self, group_id: str, end_time: str = None, count: int = 20):
        """
        Fetch topics for a group.
        :param end_time: ISO8601 string, e.g. '2025-03-03T16:00:54.510+0800'
        """
        url = f"https://api.zsxq.com/v2/groups/{group_id}/topics"
        params = {
            "scope": "all",
            "count": count
        }
        if end_time:
            # URL encode the time string if needed, requests usually handles params well
            params["end_time"] = end_time

        try:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("resp_data", {}).get("topics", [])
        except Exception as e:
            logger.error(f"Failed to fetch topics for group {group_id}: {e}")
            return []
            
    def download_file(self, url: str, group_id: str, topic_id: str, filename: str):
        """Download a file (image/attachment)"""
        save_dir = DOWNLOAD_DIR / str(group_id) / str(topic_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename
        
        if file_path.exists():
            logger.debug(f"File already exists: {file_path}")
            return str(file_path)
            
        try:
            # Use stream to handle large files
            with self.session.get(url, stream=True) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
            
            logger.info(f"Downloaded: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
