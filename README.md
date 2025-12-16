# 知识星球 (ZSXQ) -> 飞书多维表格 (Feishu Base) 同步工具

本项目用于自动采集腾讯知识星球的订阅内容（文字、图片），并将其同步归档至飞书多维表格中。支持自动登录（基于 Playwright）、增量更新、图片本地化下载及去重。

## 核心实现逻辑

系统主要由以下四个模块组成：

1.  **认证模块 (`src.zsxq_auth`)**:
    *   **问题**: 知识星球强制要求微信扫码/验证码登录，无法纯后台自动化。
    *   **方案**: 使用 `Playwright` 启动有头浏览器 (Headed Mode) 引导用户手动扫码。成功登录后，自动捕获并在本地保存 `auth.json` (包含 Cookies 和 Storage State)。
    *   **保活**: 后续运行可以直接加载 `auth.json` 实现无头自动登录。

2.  **星球客户端 (`src.zsxq_client`)**:
    *   加载 `auth.json` 恢复会话。
    *   `get_groups()`: 获取当前账号订阅的所有星球。
    *   `get_topics()`: 获取星球内的话题列表。支持分页和时间游标（用于增量更新）。
    *   `download_file()`: 将图片/附件下载至本地 `downloads/` 目录。

3.  **飞书客户端 (`src.feishu_client`)**:
    *   自动管理 `tenant_access_token` 的获取与刷新。
    *   `check_exists()`: 根据 `topic_id` 查询多维表格，防止重复抓取。
    *   `add_topic()`: 将话题内容、图片本地路径写入多维表格。

4.  **主流程 (`src.main`)**:
    *   初始化各客户端。
    *   遍历所有星球群组。
    *   获取最新话题 -> 飞书查重 -> (不存在) -> 下载图片 -> 写入飞书。

## 环境准备

1.  **Python 环境**:
    确保已安装 Python 3.8+。
    ```bash
    # 创建虚拟环境
    python -m venv venv
    # 激活环境 (Windows)
    .\venv\Scripts\activate
    # 安装依赖
    pip install -r requirements.txt
    # 安装 Playwright 浏览器内核
    playwright install chromium
    ```

2.  **配置文件**:
    将 `.env.example` 重命名为 `.env`，并填入以下配置：
    ```ini
    # 飞书应用配置 (自建应用)
    FEISHU_APP_ID=cli_xxxxxxxx
    FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
    # 多维表格配置
    FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxxxx (Base链接中获取)
    FEISHU_TABLE_ID=tblxxxxxxxxxxxx (数据表ID)
    ```

## 使用指南

### 1. 首次登录 (生成 Auth 文件)
首次运行或 Cookie 失效时，需运行认证脚本：
```bash
python -m src.zsxq_auth
```
*   程序会弹出一个 Chrome 窗口，请在 **5分钟内** 完成微信扫码登录。
*   登录成功后，窗口会自动关闭，并生成 `auth.json` 文件。

### 2. 启动采集
登录状态具备后，运行主程序开始采集：
```bash
python -m src.main
```
或直接双击运行 `run.bat` (Windows)。

## 项目结构
```
xiuqiu_crawl/
├── run.bat              # Windows 启动脚本
├── requirements.txt     # 依赖列表
├── .env                 # 配置文件 (需手动创建)
├── auth.json            # 登录凭证 (自动生成)
├── downloads/           # 下载资源存储目录
└── src/
    ├── config.py        # 配置加载
    ├── main.py          # 主入口
    ├── zsxq_auth.py     # 登录认证脚本
    ├── zsxq_client.py   # 星球 API 封装
    ├── feishu_client.py # 飞书 API 封装
    └── research_file_api.py # (开发用) 附件接口调研脚本
```

## 注意事项
*   **附件下载**: 由于知识星球附件下载接口较为隐蔽，目前主要支持 **图片下载**。附件下载逻辑已预留，需配合抓包进一步分析。
*   **频率限制**: 脚本中包含简单的 `time.sleep` 延时，避免触发反爬策略。
