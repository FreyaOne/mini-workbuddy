"""第 8 章：长任务不迷路。

比上一章多了什么：
  1. 计划模式：把任务清单交给 Agent 自己维护（TaskCreate / TaskUpdate / TaskList）
  2. 上下文闸门：接近窗口上限时自动压缩成摘要
  3. 运行时注入：时间、任务数、上下文用量通过 HintBlock 注入，而不是写死在 system prompt 里
"""

import asyncio
import os

from dotenv import load_dotenv

from agentscope.agent import Agent, ContextConfig, InjectionConfig
from agentscope.credential import OpenAICredential
from agentscope.event import EventType
from agentscope.message import UserMsg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionMode
from agentscope.tool import TaskCreate, TaskGet, TaskList, TaskUpdate, Toolkit
from agentscope.workspace import LocalWorkspace

load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

WORKDIR = "./sandbox"

# 上下文窗口大小。真实值取决于模型，这里显式声明，压缩阈值按它计算。
CONTEXT_SIZE = 32_768


def build_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=API_KEY, base_url=BASE_URL or None),
        model=MODEL_NAME,
        context_size=CONTEXT_SIZE,
    )


def prepare_files() -> None:
    """放三份材料进去。「整理工作区」这个任务要有东西可整理才看得出效果。"""
    files = {
        "plan.txt": "1. 完成数据采集\n2. 清洗脚本重写\n3. 导出模块联调\n",
        "meeting.md": "# 周一例会\n\n- 采集模块验收通过\n- 清洗模块延期两天\n- 下周同步导出接口\n",
        "note.txt": "清洗模块的边界情况：空行、全角逗号、末尾换行。\n",
    }
    for name, body in files.items():
        with open(os.path.join(WORKDIR, name), "w", encoding="utf-8") as f:
            f.write(body)


def render(event) -> None:
    if event.type == EventType.TEXT_BLOCK_DELTA:
        print(getattr(event, "delta", ""), end="", flush=True)
    elif event.type == EventType.TOOL_CALL_START:
        print(f"\n  → {getattr(event, 'tool_call_name', '')}", flush=True)
    elif event.type == EventType.HINT_BLOCK:
        # 运行时注入：时间、任务状态、上下文用量都从这里进来
        print(f"  [注入] {getattr(event, 'hint', '')[:70]}", flush=True)


def describe_state(agent: Agent) -> None:
    """把不轻易看见的三样东西打出来：任务、摘要、上下文条数。"""
    tasks = agent.state.tasks_context.tasks
    print("\n" + "-" * 70)
    print(f"任务清单（{len(tasks)} 条）")
    for task in tasks:
        print(f"  {task.id:<3} [{task.state:<11}] {task.subject}")

    context_len = len(agent.state.context)
    summary_len = len(agent.state.summary or "")
    print(f"上下文消息数：{context_len}　摘要长度：{summary_len} 字")
    print("-" * 70 + "\n")


async def main() -> None:
    os.makedirs(WORKDIR, exist_ok=True)
    prepare_files()

    async with LocalWorkspace(workdir=WORKDIR) as workspace:
        workspace_tools = await workspace.list_tools()
        instructions = await workspace.get_instructions()

        toolkit = Toolkit(
            tools=[
                *workspace_tools,
                # 四个任务工具，框架把 agent.state 自动注入给它们
                TaskCreate(),
                TaskList(),
                TaskUpdate(),
                TaskGet(),
            ],
        )

        agent = Agent(
            name="Buddy",
            system_prompt=(
                "你叫 Buddy，做事之前先列计划。"
                "任务超过三步时，用 TaskCreate 建清单，"
                "开始做时用 TaskUpdate 标记 in_progress，做完标记 completed。"
                "\n\n" + instructions
            ),
            model=build_model(),
            toolkit=toolkit,
            offloader=workspace,
            # 上下文闸门：用到 80% 时压缩，压缩后保留 10% 的空间
            context_config=ContextConfig(
                trigger_ratio=0.8,
                reserve_ratio=0.1,
                tool_result_limit=50_000,
            ),
            # 运行时注入：时间按上海时区，半小时内不重复注入
            injection_config=InjectionConfig(
                timezone="Asia/Shanghai",
                time_format="%Y-%m-%d %H:%M",
                time_interval=0.5,
            ),
        )
        # 这一章的重点是计划模式与上下文压缩，脚本里没有确认界面。
        # 用 DEFAULT 会在第一次写文件时停下来等人点头，然后就没有下文了。
        # 权限本身是第 7 章的主题，这里先放行。
        agent.state.permission_context.mode = PermissionMode.BYPASS

        question = (
            "帮我整理一下工作区：先看看有哪些文件，"
            "然后为每个文件写一行摘要，最后汇总成 README.summary.md。"
        )
        print(f">>> 你：{question}\n")

        async for event in agent.reply_stream(UserMsg(name="user", content=question)):
            render(event)

        print()
        describe_state(agent)


if __name__ == "__main__":
    asyncio.run(main())
