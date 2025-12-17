import requests
import time
import os
import zlib
from requests_toolbelt.multipart.encoder import MultipartEncoder
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
        # 显式指定 Header，防止 requests 自动处理出现意外（参考用户代码）
        # 虽然 requests 默认 json=... 会带 Content-Type，但显式更安全
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

    def get_auth_headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}"
        }

    def upload_bitable_file(self, file_path: str, file_type: str = "file") -> str:
        """
        上传文件到多维表格专用的云空间，返回 file_token。
        根据用户示例代码重构：使用 MultipartEncoder。
        :param file_path: 本地文件路径
        :param file_type: "image" or "file" (虽然API层都是bitable_file/image，这里做区分)
        :return: file_token
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        token = self._get_token()
        
        # 确定 parent_type
        # 用户代码中：
        # upload_file_to_drive -> explorer (Drive)
        # upload_media_to_drive -> bitable_file (Attachment)
        # 经过测试，存入附件字段建议统一使用 bitable_file，避免 400 错误
        real_parent_type = "bitable_file"
        
        # 父节点对于 bitable 上传，需要是 app_token
        parent_node = self.app_token 
        
        headers = {"Authorization": f"Bearer {token}"}

        # 1) 小文件：直接上传 (<= 20MB)
        if file_size <= 20 * 1024 * 1024:
            url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
            
            form_data = {
                "file_name": file_name,
                "parent_type": real_parent_type,
                "parent_node": parent_node,
                "size": str(file_size),
                # file 字段需要 (filename, file_object, content_type)
                "file": (file_name, open(file_path, "rb"), "application/octet-stream") 
            }
            
            try:
                m = MultipartEncoder(form_data)
                headers["Content-Type"] = m.content_type
                
                resp = requests.post(url, headers=headers, data=m, timeout=300)
                resp.raise_for_status()
                res_json = resp.json()
                
                if res_json.get("code") != 0:
                    logger.error(f"Upload failed: {res_json}")
                    return None
                    
                data = res_json.get("data", {})
                file_token = data.get("file_token")
                logger.info(f"Uploaded {file_name} -> {file_token}")
                return file_token
                
            except Exception as e:
                logger.error(f"Error uploading file {file_path}: {e}")
                return None
                
        else:
            # 2) 大文件：分片上传 (简化版，参考用户逻辑)
            logger.info(f"File {file_name} > 20MB, using chunked upload (Logic pending full impl).")
            # 暂时为了稳定性，如果真的遇到超大文件，建议暂不处理或报错，避免逻辑过于复杂。
            # 或者复用用户代码的逻辑。
            return self._upload_large_file(file_path, real_parent_type, parent_node, token)

    def _upload_large_file(self, file_path, parent_type, parent_node, token):
        # 预上传
        file_name = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        headers = {"Authorization": f"Bearer {token}"}
        
        prep_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_prepare"
        body = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": size
        }
        try:
            r = requests.post(prep_url, headers={**headers, "Content-Type": "application/json"}, json=body, timeout=10)
            r.raise_for_status()
            prep = r.json().get("data", {})
            upload_id = prep["upload_id"]
            block_size = prep["block_size"]
            block_num = prep["block_num"]
            
            # 分片上传
            part_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_part"
            with open(file_path, "rb") as f:
                for seq in range(block_num):
                    chunk = f.read(block_size)
                    checksum = str(zlib.adler32(chunk) & 0xFFFFFFFF)
                    mpart = MultipartEncoder({
                        "upload_id": upload_id,
                        "seq": str(seq),
                        "size": str(len(chunk)),
                        "checksum": checksum,
                        "file": (file_name, chunk, "application/octet-stream"),
                    })
                    # Content-Type 由 MultipartEncoder 生成
                    curr_headers = headers.copy()
                    curr_headers["Content-Type"] = mpart.content_type
                    
                    rp = requests.post(part_url, headers=curr_headers, data=mpart, timeout=300)
                    rp.raise_for_status()
            
            # 完成上传
            finish_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_finish"
            f_body = {"upload_id": upload_id, "block_num": block_num}
            rf = requests.post(finish_url, headers={**headers, "Content-Type": "application/json"}, json=f_body, timeout=10)
            rf.raise_for_status()
            return rf.json().get("data", {}).get("file_token")
            
        except Exception as e:
            logger.error(f"Large file upload failed: {e}")
            return None

    def search_records(self, field_name: str, field_value: str) -> list:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
        data = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": field_name,
                        "operator": "is",
                        "value": [field_value]
                    }
                ]
            },
            "automatic_fields": False 
        }
        
        try:
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json; charset=utf-8"
            
            resp = requests.post(url, json=data, headers=headers)
            resp.raise_for_status()
            res_json = resp.json()
            
            if res_json.get("code") != 0:
                logger.error(f"Search failed: {res_json}")
                return []
                
            return res_json.get("data", {}).get("items", [])
            
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            return []

    def check_exists(self, topic_id: str) -> bool:
        records = self.search_records("topic_id", topic_id)
        return len(records) > 0

    def add_topic(self, fields: dict):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        data = {"fields": fields}
        
        try:
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json; charset=utf-8"
            
            resp = requests.post(url, json=data, headers=headers)
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
