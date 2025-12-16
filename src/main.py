import time
from loguru import logger
from .config import FEISHU_TABLE_ID
from .zsxq_auth import login_and_save_state
from .zsxq_client import ZSXQClient
from .feishu_client import FeishuClient
from pathlib import Path

def main():
    logger.info("Starting ZSXQ Crawler...")
    
    # 1. Initialize Clients
    try:
        zsxq = ZSXQClient()
    except Exception as e:
        logger.warning(f"ZSXQ Auth failed: {e}")
        logger.info("Attempting to run login script...")
        try:
            login_and_save_state()
            zsxq = ZSXQClient()
        except Exception as login_error:
            logger.error(f"Login failed: {login_error}")
            return

    feishu = FeishuClient()
    
    # 2. Get Groups
    groups = zsxq.get_groups()
    logger.info(f"Found {len(groups)} groups.")
    
    for group in groups:
        group_id = str(group.get("group_id"))
        group_name = group.get("name", "Unknown")
        logger.info(f"Processing Group: {group_name} ({group_id})")
        
        # 3. Get Recent Topics (First page)
        # TODO: Implement paging if deep crawling is needed
        topics = zsxq.get_topics(group_id)
        logger.info(f"Fetched {len(topics)} topics from group.")
        
        for topic in topics:
            topic_id = str(topic.get("topic_id"))
            
            # 4. Check De-duplication
            if feishu.check_exists(topic_id):
                logger.info(f"Topic {topic_id} already exists in Feishu. Skipping.")
                continue
            
            logger.info(f"New Topic Found: {topic_id}")
            
            # 5. Parse Content
            talk = topic.get("talk", {})
            text_content = talk.get("text", "")
            create_time = topic.get("create_time")
            
            # Handle Images
            image_paths = []
            images = talk.get("images", [])
            for img in images:
                # Try large, then thumbnail
                img_url = img.get("large", {}).get("url") or img.get("thumbnail", {}).get("url")
                if img_url:
                    # Filename: image_id.jpg (or from logic)
                    img_id = img.get("image_id", str(time.time()))
                    fname = f"{img_id}.jpg"
                    local_path = zsxq.download_file(img_url, group_id, topic_id, fname)
                    if local_path:
                        image_paths.append(local_path)
            
            # Handle Files
            file_paths = []
            files = talk.get("files", [])
            for f in files:
                file_id = f.get("file_id")
                file_name = f.get("name")
                # TODO: Missing API for file_id -> download_url
                # url = zsxq.get_file_url(file_id)
                # if url:
                #     p = zsxq.download_file(url, group_id, topic_id, file_name)
                #     file_paths.append(p)
                logger.warning(f"Skipping attachment download for {file_name} (API missing)")
            
            # 6. Add to Feishu
            # Construct fields mapping based on assumptions. 
            # User needs to ensure Table has these columns or adjust code.
            record_fields = {
                "topic_id": topic_id,
                "content": text_content,
                "create_time": create_time, # Check format compatibility
                "group_name": group_name,
                "author": topic.get("show_comments", [{}])[0].get("owner", {}).get("name") if topic.get("show_comments") else "Unknown",
                # "images": ... (Feishu requires specific attachment upload flow, here we just save path string for now?)
                "local_image_paths": ", ".join(image_paths),
                "status": "Done"
            }
            
            res = feishu.add_topic(record_fields)
            if res:
                logger.success(f"Topic {topic_id} synced to Feishu.")
            else:
                logger.error(f"Failed to sync topic {topic_id}.")
                
            # Rate limit politeness
            time.sleep(1)

if __name__ == "__main__":
    main()
