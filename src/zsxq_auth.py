import time
import re
from playwright.sync_api import sync_playwright
from loguru import logger
from .config import AUTH_FILE_PATH

def login_and_save_state():
    """
    启动浏览器让用户登录知识星球。
    登录成功后保存存储状态（Cookie、LocalStorage）到文件。
    """
    
    # 尝试使用现有会话
    if AUTH_FILE_PATH.exists():
        logger.info("检测到本地认证文件，正在验证会话有效性...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(storage_state=str(AUTH_FILE_PATH))
                page = context.new_page()
                
                # 尝试访问登录页，如果已登录通常会自动跳转到首页
                check_url = "https://wx.zsxq.com/dweb2/login"
                # logger.info(f"正在导航至 {check_url} 以验证会话...")
                page.goto(check_url)
                
                # 等待 URL 变化
                try:
                    # 如果跳转到了 index 或 group，说明已登录
                    # 如果停留在 login，说明未登录
                    # 我们等待 url 不包含 login
                    page.wait_for_url(re.compile(r"^(?!.*login).*$"), timeout=5000)
                    
                    logger.success("本地会话依然有效！无需重新登录。")
                    browser.close()
                    return
                        
                except Exception:
                    # 超时意味着还在 login 页面（因为我们等待的是非login）
                    logger.warning("本地会话已失效，请重新登录。")
                
                browser.close()
        except Exception as e:
            logger.error(f"读取认证文件或启动浏览器失败: {e}，将重新开始认证流程。")


    logger.info("正在启动 Playwright 进行认证...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        login_url = "https://wx.zsxq.com/dweb2/login"
        logger.info(f"正在跳转至 {login_url}")
        page.goto(login_url)
        
        logger.info("请在浏览器窗口中扫描二维码或通过手机登录。")
        logger.info("等待登录完成（正在检测 URL 是否跳转至主页）...")
        
        try:
            # 等待 URL 切换到主 Feed/索引页面 或 group 页面
            # 正则匹配: 包含 dweb2/index 或者 group/
            page.wait_for_url(re.compile(r"https://wx\.zsxq\.com/(dweb2/index|group)/"), timeout=300000)
            
            logger.info("检测到登录成功！正在保存认证状态...")
            
            AUTH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            context.storage_state(path=str(AUTH_FILE_PATH))
            logger.info(f"认证状态已保存至: {AUTH_FILE_PATH}")
            logger.success("您现在可以运行爬虫组件了。")
            
        except Exception as e:
            logger.error(f"登录超时或失败: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # 确保当前目录在 sys.path 中，防止脚本直接运行时的相对导入错误
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    login_and_save_state()
