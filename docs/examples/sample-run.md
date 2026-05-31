# 运行示例：给阿嫲的情书

本示例来自一次本地完整运行结果，用于展示平台运行后的产物形态。原始运行文件位于 `data/report/`，该目录默认不提交到仓库。

## 输入主题

```text
给阿嫲的情书
```

## 生成产物

```text
InsightEngine：私域数据库舆情洞察报告
MediaEngine：媒体传播路径分析报告
QueryEngine：权威信息核查报告
ReportEngine：最终 HTML 综合报告
```

本地生成路径示例：

```text
data/report/insight/deep_search_report_给阿嫲的情书_20260530_191914.md
data/report/media/deep_search_report_给阿嫲的情书_20260530_192149.md
data/report/query/deep_search_report_给阿嫲的情书_20260530_192632.md
data/report/final/final_report_智能舆情分析报告_20260530_154827.html
```

## Agent 输出摘要

### InsightEngine

从本地舆情数据库中检索社交媒体内容，围绕影片《给阿嫲的情书》的讨论热度、评论情绪、平台差异和用户关注点生成私域数据分析。示例运行中，InsightEngine 重点识别了“情感共鸣”“代际记忆”“地域文化认同”等讨论方向。

### MediaEngine

从公开网络和媒体报道中检索传播信息，分析话题从电影口碑、主流媒体报道、自媒体解读到社交平台扩散的传播链路。示例运行中，MediaEngine 将传播路径概括为“文学/地域文化蓄势、影视化引爆、主流媒体介入、自媒体二次扩散”。

### QueryEngine

从权威来源和公开资料中核查事实，重点分析“阿嫲”文化符号、地方文化、非遗保护、乡土文学、侨批文化等政策和公共文化背景。示例运行中，QueryEngine 输出了“民间热、政策温”“官方政策有框架但缺专项接口”等判断。

### ReportEngine

汇总三个 Agent 的报告和 ForumEngine 讨论日志，生成最终综合分析报告。示例运行生成了 HTML 报告，包含主题背景、传播路径、民意洞察、风险判断和行动建议等章节。

## 前端运行效果

运行过程中，前端会展示：

```text
1. 主题输入框
2. Insight / Media / Query 分析进度
3. Agent 运行队列
4. Forum 协作讨论日志
5. 最终报告生成状态
```

完成后可在页面中查看报告，也可以在 `data/report/final/` 中打开最终 HTML 文件。

