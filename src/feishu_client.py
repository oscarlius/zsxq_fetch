import requests
import time
from loguru import logger
from .config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BITABLE_APP_TOKEN, FEISHU_TABLE_ID

class FeishuClient:
    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.app_token = FEISHU_BITABLE_APP_TOKEN
        self.table_id = FEISHU_TABLE_ID
        self.tenant_access_token = ""
        self.token_expire_time = 0
        
    def _get_token(self):
        """Get or refresh tenant_access_token"""
        if time.time() < self.token_expire_time:
            return self.tenant_access_token
            
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            resp = requests.post(url, json=data, headers=headers)
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("code") != 0:
                logger.error(f"Failed to get Feishu token: {res_json}")
                raise Exception(f"Feishu Auth Error: {res_json.get('msg')}")
                
            self.tenant_access_token = res_json.get("tenant_access_token")
            # Set expire time to slightly less than actual expiry (usually 7200s) to be safe
            self.token_expire_time = time.time() + res_json.get("expire", 7200) - 60
            logger.info("Successfully refreshed Feishu access token")
            return self.tenant_access_token
            
        except Exception as e:
            logger.exception("Error getting Feishu token")
            raise

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def check_exists(self, topic_id: str) -> bool:
        """Check if a topic_id already exists in the table"""
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
        
        # Assumption: The table has a field named 'topic_id'
        data = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "topic_id",
                        "operator": "is",
                        "value": [topic_id]
                    }
                ]
            },
            "view_id": None
        }
        
        try:
            resp = requests.post(url, json=data, headers=self._get_headers())
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("code") != 0:
                logger.error(f"Failed to search records: {res_json}")
                return False
                
            total = res_json.get("data", {}).get("total", 0)
            return total > 0
            
        except Exception as e:
            logger.error(f"Error checking existence for topic_id {topic_id}: {e}")
            # If error, assume false to avoid missing data, or handle otherwise? 
            # Better to log and maybe retry. For now return False but log heavy error.
            return False

    def add_topic(self, fields: dict):
        """Add a new record to Feishu Bitable"""
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        
        data = {
            "fields": fields
        }
        
        try:
            # Feishu rate limit handling could be added here
            resp = requests.post(url, json=data, headers=self._get_headers())
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("code") != 0:
                logger.error(f"Failed to add record: {res_json}")
                return None
                
            logger.info(f"Successfully added record for topic_id: {fields.get('topic_id', 'unknown')}")
            return res_json.get("data", {}).get("record", {}).get("record_id")
            
        except Exception as e:
            logger.error(f"Error adding topic: {e}")
            return None

    def update_record(self, record_id: str, fields: dict):
        """Update an existing record"""
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        
        data = {
            "fields": fields
        }
        
        try:
            resp = requests.put(url, json=data, headers=self._get_headers())
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("code") != 0:
                logger.error(f"Failed to update record {record_id}: {res_json}")
                return False
                
            logger.info(f"Successfully updated record {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating record {record_id}: {e}")
            return False
