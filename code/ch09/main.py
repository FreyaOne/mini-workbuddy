"""第 9 章：会话要活下去。

比上一章多了什么：
  1. 三个键定位一条会话：user_id / agent_id / session_id
  2. AgentState 存成 JSON，重启后原样恢复
  3. 恢复时要手动清掉的两处状态（structured_schema、cur_iter）
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.event import EventType
from agentscope.message import UserMsg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionMode
from agentscope.state import AgentState
from agentscope.tool import TaskCreate, TaskList, TaskUpdate, Toolkit
from agentscope.workspace import LocalWorkspace

from store import JsonStateStore

load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

WORKDIR = "./sandbox"
STORE_ROOT = "./.sessions"

# 三个键。生产环境里 user_id 来自登录态，agent_id 是你的智能体编号。
USER_ID = "mu"
AGENT_ID = "buddy"


def build_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=API_KEY, base_url=BASE_URL or None),
        model=MODEL_NAME,
        context_size=32_768,
    )


def render(event) -> None:
    if event.type == EventType.TEXT_BLOCK_DELTA:
        print(getattr(event, "delta", ""), end="", flush=True)
    elif event.type == EventType.TOOL_CALL_START:
        print(f"\n  → {getattr(event, 'tool_call_name', '')}", flush=True)


async def build_agent(workspace: LocalWorkspace, state: AgentState | None) -> Agent:
    """按有无历史状态，决定是新建会话还是接着聊。"""
    workspace_tools = await workspace.list_tools()
    instructions = await workspace.get_instructions()

    return Agent(
        name="Buddy",
        system_prompt="你叫 Buddy，一个文件助手。\n\n" + instructions,
        model=build_model(),
        toolkit=Toolkit(
            tools=[*workspace_tools, TaskCreate(), TaskList(), TaskUpdate()],
        ),
        offloader=workspace,
        state=state,          # None 时框架自己造一个空状态
    )


async def chat_once(agent: Agent, text: str) -> None:
    print(f"\n>>> 你：{text}")
    async for event in agent.reply_stream(UserMsg(name="user", content=text)):
        render(event)
    print()


async def main() -> None:
    store = JsonStateStore(STORE_ROOT)
    os.makedirs(WORKDIR, exist_ok=True)

    # 命令行可指定 session_id：不指定则新建
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    state = None
    if session_id:
        state = store.load(USER_ID, AGENT_ID, session_id)
        if state is None:
            print(f"会话 {session_id} 不存在，按新会话处理。")
            state = AgentState()
            state.session_id = session_id
        else:
            print("=" * 70)
            print(f"恢复会话 {session_id}")
            print(f"  历史消息 {len(state.context)} 条　摘要 {len(state.summary or '')} 字")
            print(f"  任务 {len(state.tasks_context.tasks)} 条")
            print("=" * 70)

    async with LocalWorkspace(workdir=WORKDIR) as workspace:
        agent = await build_agent(workspace, state)
        agent.state.permission_context.mode = PermissionMode.BYPASS

        session_id = agent.state.session_id
        print(f"会话 id：{session_id}（下次启动带上它就能接着聊）")

        await chat_once(agent, "记住：我的周报固定分三段，进度、问题、下周计划。")
        store.save(USER_ID, AGENT_ID, agent.state)

        await chat_once(agent, "用 TaskCreate 建三条任务，分别对应这三段。")
        store.save(USER_ID, AGENT_ID, agent.state)

        print("-" * 70)
        print("会话列表：")
        for meta in store.list_sessions(USER_ID, AGENT_ID):
            print(
                f"  {meta['session_id'][:8]}…  {meta['updated_at']}  "
                f"消息 {meta['message_count']:<3} 任务 {meta['task_count']}  {meta['title']}",
            )
        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
