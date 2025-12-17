# 知识星球 (ZSXQ) -> 飞书多维表格 (Feishu Base) 同步工具

本项目用于自动采集腾讯知识星球的订阅内容（文字、图片、附件），并将其同步归档至飞书多维表格中。支持增量更新、会话持久化、断点续传（图片/附件本地化下载）及内容去重。

## 核心功能

1.  **自动认证与会话持久化**:
    *   **扫码登录**: 首次运行时自动唤起浏览器引导微信扫码。
    *   **持久化**: 登录成功后保存 `auth.json`。
    *   **智能重用**: 每次运行时优先检测本地会话是否有效。如果有效则自动跳过扫码；如果失效则重新提示登录。
    *   **中文日志**: 所有交互提示均为中文，友好易懂。

2.  **内容采集**:
    *   **多圈子支持**: 自动获取当前账号加入的所有星球。
    *   **去重机制**: 基于 `topic_id` 在飞书中查重，避免重复写入。
    *   **资源下载**: 
        *   自动下载高清图片。
        *   自动解析并下载文件附件（PDF, Word等）。
        *   支持大文件流式下载。

3.  **飞书同步**:
    *   自动刷新 `tenant_access_token`。
    *   将主题内容、作者、时间等元数据写入多维表格。
    *   **本地路径映射**: 将下载到本地的图片和文件路径列表（逗号分隔）同步至 `local_files` 字段，方便本地索引。

## 环境准备

1.  **Python 环境**:
    需安装 Python 3.8+。
    ```bash
    # 安装依赖
    pip install -r requirements.txt
    
    # 安装 Playwright 浏览器内核 (用于登录)
    playwright install chromium
    ```

2.  **配置文件**:
    将 `.env.example` 重命名为 `.env`，并配置飞书应用信息：
    ```ini
    # 飞书自建应用凭证
    FEISHU_APP_ID=cli_xxxxxxxx
    FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
    
    # 多维表格信息
    FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxxxx
    FEISHU_TABLE_ID=tblxxxxxxxxxxxx
    ```

3.  **飞书表格结构**:
    请确保多维表格包含以下字段（详细参考 [FEISHU_SCHEMA.md](FEISHU_SCHEMA.md)）：
    *   `topic_id` (文本)
    *   `content` (文本)
    *   `local_files` (文本) - 用于存储本地文件路径
    *   `group_name`, `author`, `create_time`, `status` 等

## 使用指南

### 1. 启动采集
直接运行主程序即可，程序会自动处理登录逻辑：
```bash
python src/main.py
```

*   **首次运行**: 会自动打开浏览器窗口，请扫码登录。
*   **后续运行**: 会自动检测并复用登录状态，无需干预。

### 2. 登录状态管理
如果需要强制重新登录，可以删除目录下的 `auth.json` 文件，或直接再次运行程序（程序检测到失效会自动重试）。

## 项目结构
```
zsxq_fetch/
├── auth.json            # 自动生成的登录凭证
├── downloads/           # 下载资源存储目录 (自动按圈子/主题归档)
├── src/
│   ├── main.py          # 主程序入口
│   ├── zsxq_auth.py     # 认证与会话管理
│   ├── zsxq_client.py   # 星球 API 客户端 (含下载逻辑)
│   ├── feishu_client.py # 飞书 API 客户端
│   └── config.py        # 配置管理
├── requirements.txt     # 依赖列表
└── FEISHU_SCHEMA.md     # 飞书表格结构说明
```

## 常见问题
*   **登录超时**: 扫码时间设定由于网络原因可能需要等待，请留意控制台中文提示。
*   **下载失败**: 如果附件链接失效，程序会记录警告日志但不会中断整个流程。
