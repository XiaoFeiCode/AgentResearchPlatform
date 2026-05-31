# 多源舆情智能分析系统

一个面向网络舆情研判的多 Agent 分析平台。系统围绕同一舆情主题，组合私域数据挖掘、媒体传播检索、权威信息核查、协作讨论与报告生成流程，最终输出结构化分析报告。

## 功能概览

- 多 Agent 并行分析：Insight、Media、Query 三个分析引擎并行处理同一主题。
- 私域舆情挖掘：从本地 MySQL 中检索爬虫采集的社交媒体数据。
- 网络与权威检索：支持 Tavily、Bocha、Anspire 等搜索工具。
- 协作讨论：ForumEngine 汇总多个 Agent 的中间结果并组织讨论。
- 报告生成：ReportEngine 生成 HTML / Markdown 等格式的分析报告。
- Docker 部署：内置前端、后端、MySQL 的 Docker Compose 编排。
- 可视化前端：Vue3 工作台展示分析进度、Agent 状态和报告结果。

## 技术栈

- 前端：Vue 3、Vite
- 后端：FastAPI、Uvicorn
- Agent 编排：LangGraph、LangChain
- 数据库：MySQL 8.0
- 搜索工具：Tavily / Bocha / Anspire
- 报告渲染：HTML、WeasyPrint
- 部署：Docker、Docker Compose、Nginx
- 包管理：uv、pip requirements 导出

## 项目结构

```text
.
├── app/                     # FastAPI 应用、路由、服务层
├── engines/                 # 多 Agent 引擎
│   ├── InsightEngine/        # 私域数据库挖掘
│   ├── MediaEngine/          # 媒体/网络检索
│   ├── QueryEngine/          # 权威信息核查
│   ├── ForumEngine/          # 协作讨论
│   └── ReportEngine/         # 报告生成
├── frontend/                # Vue3 前端
├── tools/SentinelSpider/    # 舆情采集与数据库表结构初始化
├── docker-compose.yaml      # Docker Compose 编排
├── Dockerfile.backend       # 后端镜像
├── Dockerfile.frontend      # 前端镜像
├── nginx.conf               # 前端 Nginx 代理配置
├── pyproject.toml           # uv 项目依赖
├── uv.lock                  # uv 锁定文件
└── requirements.txt         # pip / Docker 兼容依赖文件
```

## 环境准备

本地开发建议：

- Python 3.12+
- uv
- Node.js 20+
- MySQL 8.0

Docker 部署建议：

- Docker
- Docker Compose

## 配置文件

复制示例配置：

```bash
cp .env.example .env
```

至少需要配置：

```env
DB_PASSWORD=your_db_password

INSIGHT_ENGINE_API_KEY=your_key
MEDIA_ENGINE_API_KEY=your_key
QUERY_ENGINE_API_KEY=your_key
REPORT_ENGINE_API_KEY=your_key
FORUM_HOST_API_KEY=your_key
KEYWORD_OPTIMIZER_API_KEY=your_key

TAVILY_API_KEY=your_tavily_key
```

真实 `.env` 不要提交到 GitHub。

## 本地开发运行

安装后端依赖：

```bash
uv sync
```

启动后端：

```bash
uv run python main.py
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

后端 API 文档：

```text
http://localhost:5000/docs
```

## Docker 部署

构建并启动：

```bash
docker compose up -d --build
```

查看服务状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

默认端口：

```text
前端：http://localhost/
后端：http://localhost:5000
MySQL：127.0.0.1:3307 -> 容器 3306
```

如果服务器 80 端口被占用，可在 `.env` 中修改：

```env
FRONTEND_PORT=8080
```

然后重新启动：

```bash
docker compose up -d
```

## 数据库数据导入

Docker MySQL 首次启动时会创建空数据库。如果本机已有 `media_crawler` 数据库，可以导出后导入到 Docker MySQL。

导出本机 MySQL：

```powershell
mysqldump -h 127.0.0.1 -P 3306 -u root -p --default-character-set=utf8mb4 --hex-blob --routines --triggers --single-transaction --result-file=media_crawler.sql media_crawler
```

导入 Docker MySQL：

```powershell
cmd /c "mysql -h 127.0.0.1 -P 3307 -u root -p --default-character-set=utf8mb4 media_crawler < media_crawler.sql"
```

验证：

```powershell
mysql -h 127.0.0.1 -P 3307 -u root -p -e "USE media_crawler; SELECT COUNT(*) FROM douyin_aweme;"
```

部署到服务器时，需要把 `media_crawler.sql` 单独传到服务器并重新导入。SQL 文件不建议提交到 GitHub。

## 舆情采集

项目集成 SentinelSpider / MediaCrawler。示例命令：

```bash
cd tools/SentinelSpider/DeepSentimentCrawling/MediaCrawler
python main.py --platform dy --lt qrcode --type search --keywords "关键词" --save_data_option db
```

采集完成后，数据会写入平台表，例如：

```text
douyin_aweme
douyin_aweme_comment
daily_news
daily_topics
```

InsightEngine 会基于这些本地数据进行私域舆情分析。

## 服务器部署流程

1. 在服务器安装 Docker 和 Docker Compose。
2. 克隆仓库：

```bash
git clone https://github.com/XiaoFeiCode/sentiment_analysis_platform.git
cd sentiment_analysis_platform
```

3. 创建并编辑 `.env`：

```bash
cp .env.example .env
nano .env
```

4. 启动服务：

```bash
docker compose up -d --build
```

5. 导入数据库数据：

```bash
docker exec -i sentinelai-db mysql -uroot -p media_crawler < media_crawler.sql
```

6. 访问：

```text
http://服务器IP/
```

## 常见问题

### 1. 提示“本地舆情数据库暂无数据”

说明当前后端连接的 MySQL 中没有平台数据。需要确认：

- Docker MySQL 是否启动
- `media_crawler` 数据库是否存在
- `douyin_aweme` 等平台表是否有数据
- 是否把本机数据导入到了 Docker MySQL

### 2. 端口被占用

如果 MySQL 3306 被本机占用，使用：

```env
DB_EXPOSE_PORT=3307
```

如果前端 80 被占用，使用：

```env
FRONTEND_PORT=8080
```

### 3. 情感分析模型加载失败

情感分析依赖 `torch`、`transformers` 和 HuggingFace 模型。默认 `.env.example` 中关闭了情感分析：

```env
SENTIMENT_ANALYSIS_ENABLED=false
ENABLE_SENTIMENT_PER_SEARCH=false
```

如果要启用，建议先下载模型到本地，再配置：

```env
SENTIMENT_MODEL_NAME=/path/to/local/sentiment/model
```
