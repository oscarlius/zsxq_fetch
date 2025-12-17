import time
import random
from datetime import datetime
from loguru import logger
from .config import FEISHU_TABLE_ID
from .zsxq_auth import login_and_save_state
from .zsxq_client import ZSXQClient
from .feishu_client import FeishuClient
from pathlib import Path

import re
import urllib.parse

def clean_content(text):
    if not text:
        return ""
    
    # Pattern to match <e type="hashtag" ... title="..." />
    pattern = r'<e type="hashtag"[^>]*?title="([^"]+)"[^>]*?/>'
    
    def replace_tag(match):
        encoded_title = match.group(1)
        try:
            # Decode URL-encoded title
            decoded_title = urllib.parse.unquote(encoded_title)
            return decoded_title
        except Exception:
            return encoded_title

    try:
        cleaned_text = re.sub(pattern, replace_tag, text)
        return cleaned_text
    except Exception as e:
        logger.error(f"Error cleaning content: {e}")
        return text

def main():
    logger.info("正在启动知识星球爬虫...")
    
    # 1. 初始化客户端
    try:
        zsxq = ZSXQClient()
    except Exception as e:
        logger.warning(f"知识星球认证失败: {e}")
        logger.info("尝试运行登录脚本...")
        try:
            login_and_save_state()
            zsxq = ZSXQClient()
        except Exception as login_error:
            logger.error(f"登录失败: {login_error}")
            return

    feishu = FeishuClient()
    
    # 2. 获取圈子列表
    groups = zsxq.get_groups()
    logger.info(f"发现 {len(groups)} 个圈子。")
    
    for group in groups:
        group_id = str(group.get("group_id"))
        group_name = group.get("name", "未知圈子")
        logger.info(f"正在处理圈子: {group_name} ({group_id})")
        
        # 3. 获取最近的主题 (第一页)
        # TODO: 如需深度爬取可实现分页逻辑
        topics = zsxq.get_topics(group_id)
        logger.info(f"从圈子获取到 {len(topics)} 个主题。")
        
        for topic in topics:
            topic_id = str(topic.get("topic_id"))
            
            # 4. 检查去重
            if feishu.check_exists(topic_id):
                logger.info(f"主题 {topic_id} 已存在于飞书表中。跳过。")
                continue
            
            logger.info(f"发现新主题: {topic_id}")
            
            # 5. 解析内容
            talk = topic.get("talk", {})
            text_content = talk.get("text", "")
            # 简单清洗，移除多余空白
            if text_content:
                text_content = text_content.strip()
                # 处理hashtag
                text_content = clean_content(text_content)

            create_time_str = topic.get("create_time") # 格式如: 2025-12-17T16:31:22.245+0800
            # 飞书日期字段需要毫秒级时间戳
            try:
                dt = datetime.strptime(create_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                create_time = int(dt.timestamp() * 1000)
            except Exception:
                # 兼容旧版或者不同格式，若解析失败则使用当前时间或原值(飞书会报错若格式不对)
                try:
                     # 尝试无微秒格式
                     dt = datetime.strptime(create_time_str.split(".")[0] + "+0800", "%Y-%m-%dT%H:%M:%S%z")
                     create_time = int(dt.timestamp() * 1000)
                except:
                     logger.warning(f"Failed to parse time: {create_time_str}, using current time")
                     create_time = int(time.time() * 1000)
            
            # 处理图片
            image_paths = []
            attachment_tokens = [] # 存储飞书附件Token
            
            images = talk.get("images", [])
            for img in images:
                # 优先尝试大图，其次缩略图
                img_url = img.get("large", {}).get("url") or img.get("thumbnail", {}).get("url")
                if img_url:
                    # 文件名: image_id.jpg
                    img_id = img.get("image_id", str(time.time()))
                    fname = f"{img_id}.jpg"
                    local_path = zsxq.download_file(img_url, group_id, topic_id, fname)
                    if local_path:
                        image_paths.append(local_path)
                        # 上传到飞书
                        logger.info(f"正在上传图片: {fname}")
                        token = feishu.upload_bitable_file(local_path, file_type="image")
                        if token:
                            attachment_tokens.append({"file_token": token})
                        else:
                             logger.error(f"图片上传失败: {fname}")
                    
                    # Prevent rate limiting
                    time.sleep(random.uniform(1.5, 3.5))
            
            # 处理文件附件
            file_paths = []
            files = talk.get("files", [])
            for f in files:
                file_id = f.get("file_id")
                file_name = f.get("name")
                if file_id:
                     url = zsxq.get_file_download_url(file_id)
                     if url:
                         logger.info(f"正在下载文件: {file_name}")
                         p = zsxq.download_file(url, group_id, topic_id, file_name)
                         if p:
                             file_paths.append(p)
                             # 上传到飞书
                             logger.info(f"正在上传文件: {file_name}")
                             token = feishu.upload_bitable_file(p, file_type="file")
                             if token:
                                 attachment_tokens.append({"file_token": token})
                             else:
                                 logger.error(f"文件上传失败: {file_name}")
                         
                         # Prevent rate limiting
                         time.sleep(random.uniform(2, 5))
                     else:
                         logger.warning(f"无法获取文件 {file_name} 的下载链接")

            
            # 6. 添加到飞书
            # 构造字段映射
            all_files = image_paths + file_paths
            record_fields = {
                "topic_id": topic_id,
                "content": text_content,
                "create_time": create_time, 
                "group_name": group_name,
                "author": topic.get("show_comments", [{}])[0].get("owner", {}).get("name") if topic.get("show_comments") else "未知作者",
                "local_files": ", ".join(all_files),
                # 如果飞书表中包含 attachments 附件列，可以直接写入
                "attachments": attachment_tokens,
                "status": "Done"
            }
            
            res = feishu.add_topic(record_fields)
            if res:
                logger.success(f"主题 {topic_id} 已同步到飞书。")
            else:
                logger.error(f"同步主题 {topic_id} 失败。")
                
            # 限流礼让
            wait_seconds = random.randint(20, 30)
            logger.info(f"等待 {wait_seconds} 秒后继续...")
            time.sleep(wait_seconds)

if __name__ == "__main__":
    # 确保当前目录在 sys.path 中，防止脚本直接运行时的相对导入错误
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    main()
