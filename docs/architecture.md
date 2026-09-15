# 架构与维护约定

## 设计范围

本项目采用分层单体，保留现有 LangGraph、Streamlit、MCP、requests 技术栈。所有可发布代码位于 `src/research_source_agent`；通过标准 Python 包安装解决导入问题，运行代码不修改 `sys.path`。

目录按实际职责划分，没有业务需求的数据库、队列和向量存储暂不建立空壳模块。

## 模块职责

| 模块 | 职责 | 主要依赖 |
| --- | --- | --- |
| `domain/articles.py` | 文献结构、字段清洗、稳定来源编号、去重与元数据合并 | Python 标准库 |
| `infrastructure/scholarly.py` | Crossref JSON、arXiv Atom 请求与响应解析 | requests、domain |
| `services/retrieval.py` | 调用数据源、失败降级、去重排序和结果统计 | infrastructure、domain |
| `tools/article_search.py` | LangChain 工具注册与输入参数约束 | services、Pydantic |
| `agents/research.py` | 模型调用、工具循环、消息状态和结果提取 | tools、config、LangGraph |
| `agents/prompts.py` | 检索与引用策略提示词 | 无 |
| `agents/models.py` | AgentResult、ToolEvent 界面契约 | Python 标准库 |
| `interfaces/web/app.py` | 会话交互、研究设置、来源展示和导出 | agents、Streamlit |
| `interfaces/mcp/server.py` | 对外暴露 MCP 检索工具 | services、MCP |
| `config.py` | 环境读取与 LangSmith 初始化 | python-dotenv |
| `cli.py` | 选择 Web 或 MCP 启动入口 | interfaces |

Web 调用链：`interfaces/web -> agents -> tools -> services -> infrastructure`。

MCP 调用链：`interfaces/mcp -> services -> infrastructure`。

领域层不依赖 UI、模型 SDK 或网络客户端。检索服务返回原有字典结构，两个接口共享同一套检索与去重规则。新增数据源先在适配器层实现，再注册到检索服务并同步工具参数约束。

## 配置与生命周期

导入包不会自动读取本地密钥。构造 Agent 或启动 MCP 时调用 `load_settings()`；应用默认读取当前工作目录的 `.env`，也支持 `RESEARCH_ENV_FILE`。部署环境变量优先，避免本地文件覆盖进程注入的配置。

Agent 可通过 `Settings` 显式传入模型配置。配置改变后重启应用，避免已有模型客户端继续使用旧配置。LangSmith 保留原有按环境变量启用的行为，MCP 的 stdio 通道不输出自定义启动日志。

Windows 启动脚本负责后台进程、端口选择、服务复用和健康探测；跨平台命令行入口负责前台运行。二者都依赖已经安装的 Python 包。

## 从旧目录迁移

| 旧路径 | 新路径 |
| --- | --- |
| `agent.py` | `src/research_source_agent/agents/research.py`、`models.py`、`prompts.py` |
| `article_search.py` | `domain/articles.py`、`infrastructure/scholarly.py`、`services/retrieval.py` |
| `tools.py` | `src/research_source_agent/tools/article_search.py` |
| `app.py` | `src/research_source_agent/interfaces/web/app.py` |
| `mcp_server.py` | `src/research_source_agent/interfaces/mcp/server.py` |
| `config.py` | `src/research_source_agent/config.py` |
| `test_*.py` | `tests/test_*.py` |
| `start_app.ps1` | `scripts/start_app.ps1` |

新导入示例：

```python
from research_source_agent.agents.research import ResearchSourceAgent
from research_source_agent.agents.models import AgentResult, ToolEvent
from research_source_agent.services.retrieval import search_articles
from research_source_agent.domain.articles import Article, deduplicate_articles
```

原包级模块路径如 `research_source_agent.article_search` 已移除；外部调用方需要同步修改导入。原来的 `Build_Graph` 方法按 Python 命名惯例调整为 `build_graph`。运行安装命令后，不再需要从项目父目录执行测试或保留原文件夹名。正在运行的旧进程需重新启动后才能使用新版本。

本地产品资料和评测结果不纳入版本库或发布包。后续有可公开的数据集和自动回归指标时，再将评测代码纳入独立 `evals/` 目录。

## 验证策略

现有测试覆盖 DOI 与标题去重、元数据合并、arXiv 年份过滤、单数据源失败降级、Agent 结果提取、MCP 工具注册，以及界面多轮交互中的警告保留。

新增配置优先级与命令入口测试。打包后的程序还应在源码目录之外验证导入和页面入口，确保 wheel 包含提示词、模型和界面脚本。

## 生产部署边界

本次完成的是工程结构、安装、测试和部署入口整理。以下运行能力仍保持现状：

- `MemorySaver` 保存进程内历史，多副本和重启恢复需要持久化检查点，并建立用户与会话的归属关系。
- 模型和数据源调用为同步请求；外部接口已有超时与部分失败降级，高并发场景仍需限流、重试策略和容量评估。
- Web 页面没有身份认证和用户额度管理。公网使用应放在有认证与 TLS 的入口后，并增加请求配额。
- 健康检查只检测 Streamlit 进程，不检查模型授权和外部学术接口。
- 引用约束目前通过提示词实现；严格生产要求下需要增加生成结果的来源编号校验。
- 直接依赖已固定版本，完整可复现发布还需锁定传递依赖并完成目标平台验证。

后续扩展优先围绕这些实际需求展开，避免只为目录完整性引入额外服务。
