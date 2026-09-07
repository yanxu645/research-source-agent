# 文献雷达：文献与文章溯源Agent

这是一个用于论文写作、行业研究和专题调研的信息获取Agent。它不代写论文，也不伪造引用；它负责把“我要研究某个主题”转成可核查的文献清单和带来源编号的研究大纲。

## 能做什么

- 同时检索Crossref与arXiv的公开元数据。
- 收集标题、作者、年份、期刊/平台、摘要、DOI和原文入口。
- 先按DOI去重，再按规范化标题与相似标题去重。
- 基于真实检索结果生成大纲，引用格式为稳定的`[S-XXXXXXX]`。
- 保留多轮对话记忆，可继续追问某个方向。
- 在界面中单独展示本轮来源、去重数量、检索次数并导出Markdown记录。

## 运行

### Windows 一键启动（推荐）

首次在另一台电脑使用时，先按下方说明创建环境和配置模型，然后双击项目内的`start_app.cmd`。它会检查项目Python环境，启动后台服务，等服务就绪后自动打开浏览器。启动窗口关闭后，后台服务继续运行。

- 默认地址是 `http://127.0.0.1:8502`；端口被其他程序占用时自动尝试后续端口，并打开实际可用地址。
- 重复双击会复用由该入口启动的健康服务，不会重复启动。
- 电脑重启或后台服务退出后，再双击此入口即可恢复。单独打开收藏的网址不会启动Python服务。
- 找不到浏览器页面时，打开项目根目录的`streamlit-8502.log`，访问其中的`URL`。每次成功启动或复用服务都会更新实际地址；即使换了端口，这个文件名也不变。文件中的检查时间是上次启动时的记录，不能保证服务此刻仍在运行。
- 最新地址和进程记录也保存在`.runtime/server.json`，详细日志在`.runtime/streamlit.log`和`.runtime/streamlit-error.log`。
- `127.0.0.1`和`localhost`都指打开浏览器的这台电脑。别人需要在自己的电脑启动项目；这些地址不是可发给他人直接访问的公网链接。
- 页面连通只表示网页服务就绪，实际检索仍需要有效的模型配置和外部接口可用。

仅启动、不打开浏览器：`powershell -NoProfile -ExecutionPolicy Bypass -File .\start_app.ps1 -NoBrowser`。

### 首次配置环境（Windows）

建议使用Python 3.10-3.12。保留项目文件夹名`research_source_agent`（代码使用这个包名）。以下命令在包含`app.py`和`requirements.txt`的文件夹执行；不需要使用作者电脑上的绝对路径，也不要复制作者的`.venv`：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

使用其他已安装的受支持版本时，将`-3.10`换为对应版本。在同一目录创建自己的`.env`，按模型服务商提供的信息填写：

```dotenv
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_name
# 使用 OpenAI 兼容服务时填写服务商的 API 基础地址：
# OPENAI_BASE_URL=https://your-provider.example/v1
```

不要共享包含真实密钥的`.env`。完成后双击`start_app.cmd`，或者执行：

```powershell
.\start_app.cmd
```


下面的测试与MCP命令在`research_source_agent`的父目录执行。

命令行验证检索模块：

```powershell
.\research_source_agent\.venv\Scripts\python.exe -m unittest research_source_agent.test_article_search
```

可选的MCP服务：

```powershell
.\research_source_agent\.venv\Scripts\python.exe -m research_source_agent.mcp_server
```

## 数据流

```text
研究设置+用户问题
        ↓
MessagesState（保存多轮消息）
        ↓
LLM判断是否需要检索
        ↓ tool_call
Crossref/arXiv公开接口
        ↓
字段清洗→DOI去重→标题相似去重
        ↓ ToolMessage（结构化来源）
LLM只使用真实ref_id生成文献表和研究大纲
        ↓
Streamlit展示答案、来源和去重统计
```

LangGraph：

```text
START→agent──无工具调用──→END
          ↓有工具调用
        tools───────────────→agent
```


Streamlit只是一层低耦合界面；删除`app.py`不影响Agent和检索业务模块。

## 证据边界

- Crossref和arXiv返回的是公开元数据与摘要，不等于Agent已阅读论文全文。
- DOI链接可能进入出版商页面，全文是否开放取决于版权和机构权限。
- 中文数据库（例如知网、万方）没有开放通用检索接口，因此当前版本不绕过登录或版权限制。
- 最终用于论文前，应由作者打开原文，核对页码、研究方法和结论语境。
