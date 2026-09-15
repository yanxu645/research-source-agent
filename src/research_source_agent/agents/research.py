"""基于 LangGraph ReAct 循环的文献溯源 Agent。"""

from __future__ import annotations
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from research_source_agent.config import Settings, configure_langsmith, load_settings
from research_source_agent.tools.article_search import TOOLS
from research_source_agent.agents.models import AgentResult, ToolEvent
from research_source_agent.agents.prompts import SYSTEM_PROMPT

def content_to_str(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return ''.join(elem.get('text', '') if isinstance(elem, dict) else str(elem)
                       for elem in content)

    return str(content)

class ResearchSourceAgent:
    def __init__(self, settings: Settings | None = None):
        settings = settings or load_settings()
        configure_langsmith('ResearchSourceAgent')

        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            temperature= 0
        )

        self.llm_with_tools = self.llm.bind_tools(TOOLS)
        self.graph = self.build_graph()


    def build_graph(self):
        def call_model(state:MessagesState):
            messages = [SystemMessage(content=SYSTEM_PROMPT)]+state['messages']
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
