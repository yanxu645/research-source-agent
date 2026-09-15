# 文献雷达：文献与文章溯源Agent

基于LangGraph的文献检索与溯源助手，提供Streamlit页面和MCP工具。检索Crossref、arXiv的公开元数据，按DOI与标题去重，生成带真实来源编号的文献清单和研究大纲。

## 项目结构

采用可安装的Python`src`布局，项目文件夹可以自由命名。业务代码、测试、启动脚本和文档分别管理。

```text
.
├── src/research_source_agent/
│   ├── agents/                 # LangGraph编排、提示词、运行结果
│   ├── domain/                 # 文献模型、字段规范化与去重规则
│   ├── services/               # 多源检索、排序、失败降级
│   ├── infrastructure/         # Crossref/arXiv HTTP适配器
│   ├── tools/                  # LangChain工具与参数约束
│   ├── interfaces/
│   │   ├── web/app.py          # Streamlit界面
│   │   └── mcp/server.py       # MCP服务
│   ├── config.py               # 环境配置
│   ├── cli.py                  # 统一命令行入口
│   └── __main__.py
├── tests/                      # 离线单元与界面回归测试
├── scripts/start_app.ps1        # Windows后台启动与健康检查
├── docs/architecture.md         # 模块边界、迁移说明、部署边界
├── .github/workflows/ci.yml     # 自动测试与打包
├── .streamlit/config.toml       # 界面配置
├── .env.example                # 环境变量示例
├── pyproject.toml              # 包元数据、依赖版本和命令入口
├── requirements.txt            # 安装本项目，依赖以pyproject为准
└── start_app.cmd                # Windows双击入口
```


## 安装与配置

建议使用Python 3.10或3.12。以下命令全部在项目根目录运行：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

已有虚拟环境只需重新执行安装命令，让Python注册新的`src`包。不要覆盖已有的`.env`。

在`.env`中填写模型服务信息：

```dotenv
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_name
# OPENAI_BASE_URL=https://your-provider.example/v1
```

配置优先级：**进程环境变量 > .env > 默认值**。默认读取工作目录的`.env`；从其他目录启动时，可用`RESEARCH_ENV_FILE`指定配置文件绝对路径。修改配置后需重启服务。API Key通过运行环境提供，不进入版本库。

可选配置包括`CROSSREF_MAILTO`和LangSmith追踪，参见`.env.example`。

## 启动

### Windows 一键启动

双击根目录`start_app.cmd`，或执行：

```powershell
.\start_app.cmd
```

默认地址为 http://127.0.0.1:8502。端口被占用时自动尝试后续端口，重复启动会复用该入口创建的健康服务。关闭启动窗口后，后台服务继续运行。

只启动服务、不打开浏览器：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_app.ps1 -NoBrowser
```

实际地址记录在`.runtime/server.json`和根目录`streamlit-8502.log`。详细日志位于`.runtime/`。健康检查通过表示网页服务可用，检索还需要有效的模型配置和外部网络。

### 命令行启动

```powershell
.\.venv\Scripts\python.exe -m research_source_agent web
.\.venv\Scripts\python.exe -m research_source_agent web --server.port=8503
```

激活虚拟环境后也可以运行`research-source-agent web`。命令行入口在前台运行，使用Ctrl+C停止；它不会自动寻找空闲端口。

### MCP 服务

```powershell
.\.venv\Scripts\python.exe -m research_source_agent mcp
```

也可以使用安装后的`research-source-mcp`命令。默认使用stdio，客户端应配置该虚拟环境中的可执行文件绝对路径。MCP工具直接调用检索服务，不依赖模型API Key；如需读取指定`.env`，在客户端环境中设置`RESEARCH_ENV_FILE`。

## 测试与构建

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip wheel --no-deps --wheel-dir dist .
```

测试使用模拟数据源和模型，不消耗模型额度。CI在Python 3.10、3.12下安装项目、执行测试并构建wheel。直接依赖版本集中固定在`pyproject.toml`；目前尚未提供包含所有传递依赖的锁文件。

## 证据边界

- 数据源返回公开元数据和摘要，不代表已阅读论文全文。
- DOI页面中的全文访问权限取决于版权和机构授权。
- 不绕过中文数据库的登录或版权限制。
- 正式引用前，需打开原文核对研究方法、结论语境及页码。
