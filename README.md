# 多源舆情智能分析系统

基于 FastAPI、Vue3、LangGraph 和 MySQL 的多 Agent 舆情分析平台。系统输入一个舆情主题后，会并行调用多个分析引擎，汇总本地数据库、网络媒体和权威来源的信息，并生成结构化分析报告。

## 架构图

```mermaid
flowchart LR
  Frontend[Vue3 前端] --> Backend[FastAPI 后端]
  Backend --> Insight[InsightEngine 私域数据分析]
  Backend --> Media[MediaEngine 媒体检索]
  Backend --> Query[QueryEngine 权威核查]
  Insight --> Forum[ForumEngine 协作讨论]
  Media --> Forum
  Query --> Forum
  Forum --> Report[ReportEngine 报告生成]
  Spider[SentinelSpider 爬虫] --> MySQL[(MySQL)]
  MySQL --> Insight
```

## 运行前准备

本地开发环境：

```text
Python 3.12+
uv
Node.js 20+
MySQL 8.0
```

Docker 部署环境：

```text
Docker
Docker Compose
```

## 配置

复制配置模板：

```bash
cp .env.example .env
```

主要需要填写这些配置：

```env
# 数据库
DB_DIALECT=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=media_crawler
DB_CHARSET=utf8mb4

# Docker MySQL 映射端口，本机 3306 被占用时用 3307
DB_EXPOSE_PORT=3307

# 前端端口
FRONTEND_PORT=80

# Agent 大模型配置
INSIGHT_ENGINE_API_KEY=your_key
INSIGHT_ENGINE_BASE_URL=https://api.deepseek.com
INSIGHT_ENGINE_MODEL_NAME=deepseek-v4-pro

MEDIA_ENGINE_API_KEY=your_key
MEDIA_ENGINE_BASE_URL=https://api.deepseek.com
MEDIA_ENGINE_MODEL_NAME=deepseek-v4-pro

QUERY_ENGINE_API_KEY=your_key
QUERY_ENGINE_BASE_URL=https://api.deepseek.com
QUERY_ENGINE_MODEL_NAME=deepseek-v4-pro

REPORT_ENGINE_API_KEY=your_key
REPORT_ENGINE_BASE_URL=https://api.deepseek.com
REPORT_ENGINE_MODEL_NAME=deepseek-v4-pro

FORUM_HOST_API_KEY=your_key
FORUM_HOST_BASE_URL=https://api.deepseek.com
FORUM_HOST_MODEL_NAME=deepseek-v4-pro

KEYWORD_OPTIMIZER_API_KEY=your_key
KEYWORD_OPTIMIZER_BASE_URL=https://api.deepseek.com
KEYWORD_OPTIMIZER_MODEL_NAME=deepseek-v4-pro

# 搜索工具
SEARCH_TOOL_TYPE=TavilyAPI
TAVILY_API_KEY=your_tavily_api_key
```

如果不需要本地情感分析模型，保持默认关闭即可：

```env
SENTIMENT_ANALYSIS_ENABLED=false
ENABLE_SENTIMENT_PER_SEARCH=false
```

## 本地运行

安装后端依赖：

```bash
uv sync
```

启动后端：

```bash
uv run python main.py
```

后端 API 文档：

```text
http://localhost:5000/docs
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

前端访问地址：

```text
http://localhost:5173
```

## Docker 运行

构建并启动：

```bash
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

默认访问地址：

```text
前端：http://localhost/
后端：http://localhost:5000
MySQL：127.0.0.1:3307
```

如果服务器 80 端口被占用，修改 `.env`：

```env
FRONTEND_PORT=8080
```

然后重新启动：

```bash
docker compose up -d
```

## 数据库初始化和导入

Docker 启动时会自动创建数据库表，但不会自动带入你本机已有的爬虫数据。

从本机 MySQL 导出：

```powershell
mysqldump -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 --hex-blob --routines --triggers --single-transaction --result-file=media_crawler.sql media_crawler
```

导入 Docker MySQL：

```powershell
cmd /c "mysql -h 127.0.0.1 -P 3307 -u root -p --default-character-set=utf8mb4 media_crawler < media_crawler.sql"
```

验证导入结果：

```powershell
mysql -h 127.0.0.1 -P 3307 -u root -p -e "USE media_crawler; SHOW TABLES; SELECT COUNT(*) FROM douyin_aweme;"
```

部署到服务器时，需要把 `media_crawler.sql` 单独传到服务器并重新导入。

## 爬虫采集示例

进入 MediaCrawler 目录：

```bash
cd tools/SentinelSpider/DeepSentimentCrawling/MediaCrawler
```

按关键词采集抖音数据并写入数据库：

```bash
python main.py --platform dy --lt qrcode --type search --keywords "给阿嫲的情书" --save_data_option db
```

常见写入表：

```text
douyin_aweme
douyin_aweme_comment
daily_news
daily_topics
```

## 服务器部署

在服务器拉取代码：

```bash
git clone https://github.com/XiaoFeiCode/sentiment_analysis_platform.git
cd sentiment_analysis_platform
```

创建配置：

```bash
cp .env.example .env
nano .env
```

启动服务：

```bash
docker compose up -d --build
```

如果需要导入本机数据，先上传 `media_crawler.sql`，然后执行：

```bash
docker exec -i sentinelai-db mysql -uroot -p media_crawler < media_crawler.sql
```

访问：

```text
http://服务器IP/
```

## 运行示例

示例文件位于：

```text
docs/examples/
```

当前示例包含一次完整运行后生成的最终 HTML 报告，主题为：

```text
给阿嫲的情书
```

可直接打开：

```text
docs/examples/final_report_智能舆情分析报告_20260530_154827.html
```
