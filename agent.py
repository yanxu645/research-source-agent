# """基于基础LangGraph ReAct循环的文献溯源Agent。"""

from __future__ import annotations
import json
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from research_source_agent.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    configure_langsmith,
)
from research_source_agent.tools import TOOLS

system_prompt="""
你是“文献雷达”。负责完成论文写作和专题研究时的检索、去重、溯源和大纲整理。

工作规则：
1.用户需要相关文章、引用出处、研究现状或研究大纲时，必须先调用search_scholarly_articles，不得凭记忆编造文献。
2.主题过宽时，把它改写成一个明确检索式。通常检索一次即可，确有必要时最多补充一次不同关键词的检索。
3.优先保留DOI，没有DOI时保留arXiv原文页。作者、年份、期刊等缺失时写“元数据未提供”，不能猜测。
4.清楚区分“元数据/摘要支持的结论”和“仍需阅读全文验证的判断”。不能声称已经阅读付费墙后的全文。
5.如果数据源失败或结果不足，明确说明缺口并给出下一组建议检索词。
6.只能引用工具真实返回的ref_id。每个事实或大纲论点后使用[S-XXXXXXX]，不能生成工具结果中不存在的编号。
7.用中文回答，文献标题保留原文，不要输出思维链，只输出可核查的结果。


默认输出结构：
1.检索说明：实际检索词、年份范围、数据源、去重数据
2.文献清单：引用编号、标题、作者（前三位）、年份、期刊/平台、DOI或原文链接、与主题的关系。
3.研究大纲：三级以内的大纲，每个有文献依据的要点带引用编号。
4.证据边界：哪些来自摘要，哪些必须阅读全文确认。
5.下一步：最值得补充的关键词或证据缺口。
"""

@dataclass
class ToolEvent:
    name:str #工具名
    query: str = ""  # 检索词
    unique_count: int = 0 #去重后的文献数
    duplicates_removed: int = 0 #重复文献数
    warnings: list[str] = field(default_factory=list) #警告信息
    articles: list[dict] = field(default_factory=list) #文献清单

@dataclass
class AgentResult:
    answer:str #用于在聊天区域中显示的回答
    tool_events: list[ToolEvent]

def content_to_str(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return ''.join(elem.get('text', '') if isinstance(elem, dict) else str(elem)
                       for elem in content)

    return str(content)

class ResearchSourceAgent:
    def __init__(self):
        configure_langsmith('ResearchSourceAgent')

        self.llm = ChatOpenAI(
            api_key= OPENAI_API_KEY,
            model= OPENAI_MODEL,
            base_url= OPENAI_BASE_URL,
            temperature= 0
        )

        self.llm_with_tools = self.llm.bind_tools(TOOLS)
        self.graph = self.Build_Graph()


    def Build_Graph(self):
        def call_model(state:MessagesState):
            messages = [SystemMessage(content=system_prompt)]+state['messages']
            response = self.llm_with_tools.invoke(messages)
            return {'messages': [response]}

        def should_continue(state:MessagesState):
            last_msg = state['messages'][-1]

            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                return 'tools'
            return END

        workflow = StateGraph(MessagesState)
        workflow.add_node('agent', call_model)
        workflow.add_node('tools', ToolNode(TOOLS))

        workflow.add_edge(START, 'agent')
        workflow.add_edge('tools', 'agent')
        workflow.add_conditional_edges(
            'agent',
            should_continue,
            {
                'tools': 'tools',
                END: END
            }
        )

        return workflow.compile(checkpointer=MemorySaver())

    def run(self, user_input:str, thread_id:str) -> AgentResult:
        config={
            'configurable': {'thread_id': thread_id},
            'recursion_limit': 10,
        }

        before = self.graph.get_state(config).values
        preCnt = len(before.get('messages', [])) if before else 0

        response = self.graph.invoke(
            {'messages': [HumanMessage(content=user_input)]},
            config=config,
        )

        newMsg = response['messages'][preCnt:]

        events: list[ToolEvent] = []
        for message in newMsg:
            if not isinstance(message, ToolMessage):
                continue

            try:
                payload = json.loads(content_to_str(message.content))
            except (json.JSONDecodeError, TypeError):
                events.append(ToolEvent(name=message.name or 'tool'))
                continue
            events.append(
                ToolEvent(
                    name= message.name or 'tool',
                    query= payload.get('query', ''),
                    unique_count=payload.get("unique_count", 0),
                    duplicates_removed=payload.get("duplicates_removed", 0),
                    warnings=payload.get("warnings", []),
                    articles=payload.get("articles", []),
                )
            )

        answer_message = next((message for message in reversed(newMsg) if isinstance(message, AIMessage)), response['messages'][-1])

        return AgentResult(
            answer=content_to_str(answer_message.content),
            tool_events=events,
        )
