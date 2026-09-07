"""Streamlit 展示适配层，不包含 Agent 业务逻辑。"""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_source_agent.agent import ResearchSourceAgent


st.set_page_config(
    page_title="文献雷达",
    page_icon=":material/find_in_page:",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    """
    <style>
    :root {
        --ink: #172033;
        --muted: #667085;
        --line: #e4e7ec;
        --paper: #ffffff;
        --canvas: #f7f8fa;
        --primary: #2457d6;
        --primary-hover: #1d47b8;
        --primary-soft: #eef4ff;
        --teal: #0e806f;
        --teal-soft: #e9f7f3;
    }
    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", "Microsoft YaHei", sans-serif;
    }
    .stApp {
        background: var(--canvas);
        color: var(--ink);
    }
    [data-testid="stHeader"] {
        background: rgba(247, 248, 250, .92);
        border-bottom: 1px solid rgba(228, 231, 236, .9);
        backdrop-filter: blur(10px);
    }
    [data-testid="stSidebar"] {
        background: var(--paper);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] * { letter-spacing: 0; }
    [data-testid="stSidebarContent"] { padding-top: 1rem; }
    [data-testid="stSidebar"] label {
        color: #344054 !important;
        font-weight: 650;
    }
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="textarea"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #fbfcfd;
        border-color: #d0d5dd;
        border-radius: 6px;
    }
    [data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
    [data-testid="stSidebar"] [data-baseweb="textarea"]:focus-within,
    [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(36, 87, 214, .12);
    }
    [data-baseweb="tag"],
    [data-baseweb="slider"] [role="slider"] {
        background-color: var(--primary) !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
    }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button {
        min-height: 2.55rem;
        border-color: #d0d5dd;
        background: var(--paper);
        color: #344054;
        font-weight: 650;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stDownloadButton > button:hover {
        border-color: var(--primary);
        background: var(--primary-soft);
        color: var(--primary);
    }
    .block-container {
        max-width: 1480px;
        padding: 4.5rem 2.35rem 7rem;
    }
    h1, h2, h3 { letter-spacing: 0; color: var(--ink); }
    .sidebar-header {
        padding: .15rem 0 .85rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1rem;
    }
    .sidebar-kicker {
        color: var(--primary);
        font-size: .72rem;
        font-weight: 750;
        margin-bottom: .2rem;
    }
    .sidebar-title {
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 750;
    }
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0 0 1.35rem;
    }
    .brand-lockup { display: flex; align-items: center; gap: .85rem; }
    .brand-mark {
        width: 44px;
        height: 44px;
        display: grid;
        place-items: center;
        background: var(--primary);
        color: white;
        border-radius: 8px;
        font-size: 1.05rem;
        font-weight: 800;
        box-shadow: 0 5px 14px rgba(36, 87, 214, .18);
    }
    .brand-title {
        font-size: 1.42rem;
        line-height: 1.15;
        font-weight: 780;
        color: var(--ink);
    }
    .brand-subtitle {
        margin-top: .22rem;
        color: var(--muted);
        font-size: .84rem;
    }
    .header-meta {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        color: var(--muted);
        font-size: .82rem;
        font-weight: 600;
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 8px;
        margin-bottom: 1.7rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .03);
    }
    .metric-cell { padding: .95rem 1.15rem; min-width: 0; }
    .metric-cell + .metric-cell { border-left: 1px solid var(--line); }
    .metric-label {
        color: var(--muted);
        font-size: .78rem;
        font-weight: 600;
        margin-bottom: .3rem;
    }
    .metric-value {
        color: var(--ink);
        font-size: 1.55rem;
        line-height: 1;
        font-weight: 750;
    }
    .metric-accent { color: var(--teal); }
    .section-kicker {
        color: var(--primary);
        font-size: .72rem;
        font-weight: 750;
        margin-bottom: .28rem;
    }
    .section-title {
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 750;
        margin-bottom: .25rem;
    }
    .section-note {
        color: var(--muted);
        font-size: .82rem;
        margin-bottom: 1.05rem;
    }
    div[data-testid="stChatMessage"] {
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: .85rem .9rem 1rem;
        margin-bottom: .65rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .025);
    }
    div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"] {
        background: var(--primary);
    }
    div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] {
        background: var(--teal-soft);
        color: var(--teal);
    }
    [data-testid="stChatInput"] {
        border: 1px solid #cbd2dc;
        border-radius: 8px;
        background: var(--paper);
        box-shadow: 0 12px 32px rgba(16, 24, 40, .1);
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(36, 87, 214, .12), 0 12px 32px rgba(16, 24, 40, .1);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--paper);
        border-color: var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .025);
    }
    [data-testid="stLinkButton"] a {
        min-height: 2.15rem;
        border-radius: 6px;
        border-color: #c9d3ea;
        color: var(--primary);
        background: var(--primary-soft);
        font-weight: 650;
    }
    [data-testid="stLinkButton"] a:hover {
        border-color: var(--primary);
        color: var(--primary-hover);
    }
    [data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px dashed #cbd2dc;
        background: rgba(255, 255, 255, .58);
        color: #344054;
    }
    [data-testid="stAlertContainer"] {
        background: transparent !important;
    }
    .quick-label {
        color: #475467;
        font-size: .76rem;
        font-weight: 700;
        margin: .9rem 0 .5rem;
    }
    [data-testid="stMain"] .stButton > button {
        min-height: 2.55rem;
        border-color: #d0d5dd;
        border-radius: 6px;
        color: #344054;
        background: var(--paper);
        font-weight: 650;
    }
    [data-testid="stMain"] .stButton > button:hover {
        border-color: var(--primary);
        color: var(--primary);
        background: var(--primary-soft);
    }
    button, a {
        transition: background-color .15s ease, border-color .15s ease, color .15s ease;
    }
    @media (max-width: 1100px) {
        .block-container { padding-left: 1.5rem; padding-right: 1.5rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_agent() -> ResearchSourceAgent:
    return ResearchSourceAgent()


def reset_session() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.last_articles = []
    st.session_state.last_stats = {"unique": 0, "duplicates": 0, "queries": 0}


def transcript_markdown() -> str:
    lines = ["# 文献雷达研究记录", ""]
    for message in st.session_state.messages:
        role = "研究问题" if message["role"] == "user" else "Agent 结果"
        lines.extend((f"## {role}", "", message["content"], ""))
    return "\n".join(lines)


if "thread_id" not in st.session_state:
    reset_session()

with st.sidebar:
    st.markdown(
        '<div class="sidebar-header">'
        '<div class="sidebar-kicker">检索设置</div>'
        '<div class="sidebar-title">定义研究范围</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    topic = st.text_input(
        "研究主题",
        placeholder="例如：生成式 AI 对高校写作的影响",
        help="可留空，系统会直接使用研究任务作为主题。",
    )
    focus = st.text_area(
        "关注重点",
        placeholder="例如：学习效果、学术诚信、教师干预",
        height=92,
        help="填写希望优先关注的角度，多个角度可用顿号分隔。",
    )
    year_from = st.number_input(
        "最早发表年份",
        min_value=1900,
        max_value=date.today().year,
        value=max(2020, date.today().year - 5),
        step=1,
        help="检索结果将不早于该年份。",
    )
    result_limit = st.slider(
        "文献数量",
        min_value=4,
        max_value=12,
        value=8,
        help="控制每次检索期望返回的文献数量。",
    )
    sources = st.multiselect(
        "公开数据源",
        options=["crossref", "arxiv"],
        default=["crossref", "arxiv"],
        format_func=lambda value: {"crossref": "Crossref", "arxiv": "arXiv"}[value],
        help="Crossref 覆盖广泛的出版物元数据；arXiv 偏向预印本。",
    )
    search_ready = bool(sources)
    if not search_ready:
        st.warning("请至少保留一个数据源。")
    st.divider()
    st.caption(f"本次会话 · {st.session_state.thread_id[:8].upper()} · {len(st.session_state.messages)} 条消息")
    if st.button("新建研究", icon=":material/add:", use_container_width=True):
        reset_session()
        st.rerun()
    st.download_button(
        "导出记录",
        data=transcript_markdown(),
        file_name="research-source-report.md",
        mime="text/markdown",
        icon=":material/download:",
        use_container_width=True,
        disabled=not st.session_state.messages,
    )

st.markdown(
    """
    <div class="app-header">
        <div class="brand-lockup">
            <div class="brand-mark">文</div>
            <div>
                <div class="brand-title">文献雷达</div>
                <div class="brand-subtitle">研究来源工作台</div>
            </div>
        </div>
        <div class="header-meta">Crossref + arXiv</div>
    </div>
    """,
    unsafe_allow_html=True,
)

stats = st.session_state.last_stats
if any(stats.values()):
    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-cell">
                <div class="metric-label">有效来源</div>
                <div class="metric-value">{stats['unique']}</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">合并重复</div>
                <div class="metric-value metric-accent">{stats['duplicates']}</div>
            </div>
            <div class="metric-cell">
                <div class="metric-label">检索轮次</div>
                <div class="metric-value">{stats['queries']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

chat_col, source_col = st.columns([1.45, 1], gap="large")
suggested_prompt = None

with chat_col:
    st.markdown(
        '<div class="section-kicker">研究空间</div>'
        '<div class="section-title">研究任务</div>'
        f'<div class="section-note">当前会话 · {len(st.session_state.messages)} 条消息</div>',
        unsafe_allow_html=True,
    )
    if not st.session_state.messages:
        st.info("暂无研究记录", icon=":material/travel_explore:")
        st.markdown('<div class="quick-label">快捷任务</div>', unsafe_allow_html=True)
        quick_actions = st.columns(3)
        if quick_actions[0].button(
            "生成综述大纲",
            icon=":material/account_tree:",
            use_container_width=True,
            disabled=not search_ready,
        ):
            suggested_prompt = "查找相关文献，并生成一份结构清晰的文献综述大纲"
        if quick_actions[1].button(
            "梳理研究现状",
            icon=":material/manage_search:",
            use_container_width=True,
            disabled=not search_ready,
        ):
            suggested_prompt = "查找相关文献，梳理当前研究现状、主要结论和分歧"
        if quick_actions[2].button(
            "查找证据缺口",
            icon=":material/troubleshoot:",
            use_container_width=True,
            disabled=not search_ready,
        ):
            suggested_prompt = "查找相关文献，识别目前的证据缺口并提出下一步检索方向"
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for warning in message.get("warnings", []):
                st.warning(warning)

with source_col:
    articles = st.session_state.last_articles
    st.markdown(
        '<div class="section-kicker">证据来源</div>'
        f'<div class="section-title">来源库 · {len(articles):02d}</div>'
        '<div class="section-note">本轮已核对并去重</div>',
        unsafe_allow_html=True,
    )
    if not articles:
        st.info("暂无来源", icon=":material/library_books:")
    else:
        for index, article in enumerate(articles, start=1):
            title = article.get("title") or "未命名文献"
            url = article.get("url") or ""
            authors = "、".join(article.get("authors", [])[:3]) or "作者未提供"
            meta = " · ".join(
                str(value)
                for value in (
                    authors,
                    article.get("year") or "年份未提供",
                    article.get("venue") or article.get("source_database"),
                )
                if value
            )
            with st.container(border=True):
                st.caption(f"{index:02d} · {article.get('ref_id', 'S-UNKNOWN')}")
                st.markdown(f"**{title}**")
                st.caption(meta)
                if url:
                    st.link_button("打开原文", url, icon=":material/open_in_new:")

typed_prompt = st.chat_input(
    "输入研究问题或任务",
    disabled=not search_ready,
)
prompt = suggested_prompt or typed_prompt
if prompt:
    shown_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": shown_prompt})

    context = f"""
[研究设置]
研究主题：{topic or prompt}
关注重点：{focus or '未限定'}
最早发表年份：{int(year_from)}
期望文献数量：{result_limit}
数据源：{', '.join(sources) if sources else 'crossref'}
调用检索工具时必须使用以上年份、数量和数据源参数。

[用户任务]
{prompt}
""".strip()

    with chat_col:
        with st.chat_message("user"):
            st.markdown(shown_prompt)
        with st.chat_message("assistant"):
            with st.status("正在检索并整理来源...", expanded=True) as status:
                try:
                    result = get_agent().run(context, st.session_state.thread_id)
                except Exception as error:
                    status.update(label="本轮执行失败", state="error")
                    st.error(f"执行失败：{error}")
                    st.stop()

                all_articles: dict[str, dict] = {}
                warnings: list[str] = []
                duplicate_total = 0
                for event in result.tool_events:
                    st.write(f"检索：{event.query or '未记录检索词'}")
                    st.write(f"获得 {event.unique_count} 条，去除 {event.duplicates_removed} 条重复")
                    for warning in event.warnings:
                        warnings.append(warning)
                        st.warning(warning)
                    duplicate_total += event.duplicates_removed
                    for article in event.articles:
                        all_articles[article.get("ref_id", article.get("url", ""))] = article
                status.update(label="检索与整理完成", state="complete", expanded=False)
            st.markdown(result.answer)

    st.session_state.last_articles = list(all_articles.values())
    st.session_state.last_stats = {
        "unique": len(all_articles),
        "duplicates": duplicate_total,
        "queries": len(result.tool_events),
    }
    st.session_state.messages.append(
        {"role": "assistant", "content": result.answer, "warnings": warnings}
    )
    st.rerun()
