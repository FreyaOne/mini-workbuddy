"""第 4 章（下半）：同样的任务，交给 Agent。

比上一章多了什么：
  1. 一个事件时间线打印器——把循环的每一拍都摊开
  2. ReActConfig：限制循环次数
这份打印逻辑在第 12 章会被前端原样复用。
"""

import asyncio
import os
import time

from dotenv import load_dotenv

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import OpenAICredential
from agentscope.message import UserMsg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionMode
from agentscope.tool import FunctionTool, Toolkit

from bare_loop import count_text, get_current_time

load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def build_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=API_KEY, base_url=BASE_URL or None),
        model=MODEL_NAME,
    )


def build_toolkit() -> Toolkit:
    return Toolkit(
        tools=[FunctionTool(get_current_time), FunctionTool(count_text)],
    )


# ---------------------------------------------------------------------------
# 时间线打印器：这是本章的重点，不是装饰
# ---------------------------------------------------------------------------

# 事件名 -> 缩进层级
DEPTH = {
    "REPLY_START": 0,
    "REPLY_END": 0,
    "MODEL_CALL_START": 1,
    "MODEL_CALL_END": 1,
    "TOOL_CALL_START": 2,
    "TOOL_CALL_END": 2,
    "TOOL_RESULT_START": 2,
    "TOOL_RESULT_END": 2,
    "TEXT_BLOCK_START": 2,
    "TEXT_BLOCK_END": 2,
    "THINKING_BLOCK_START": 2,
    "THINKING_BLOCK_END": 2,
}


def payload(event) -> str:
    """取出事件里值得展示的载荷。"""
    kind = event.type.value
    if kind == "TOOL_CALL_START":
        return getattr(event, "tool_call_name", "") or ""
    if kind == "TOOL_RESULT_END":
        return str(getattr(event, "state", "") or "")
    if kind == "MODEL_CALL_END":
        return (
            f"in={getattr(event, 'input_tokens', 0)} "
            f"out={getattr(event, 'output_tokens', 0)}"
        )
    if kind == "REPLY_END":
        return str(getattr(event, "finished_reason", "") or "")
    if kind == "TEXT_BLOCK_DELTA":
        return repr(getattr(event, "delta", ""))
    return ""


async def run_with_trace(agent: Agent, question: str) -> None:
    print(f">>> 你：{question}")
    print("-" * 72)

    start = time.perf_counter()
    stats = {"model_calls": 0, "tool_calls": 0, "text": [], "in": 0, "out": 0}

    async for event in agent.reply_stream(UserMsg(name="user", content=question)):
        kind = event.type.value
        elapsed = (time.perf_counter() - start) * 1000

        # 统计
        if kind == "MODEL_CALL_START":
            stats["model_calls"] += 1
        elif kind == "TOOL_CALL_START":
            stats["tool_calls"] += 1
        elif kind == "MODEL_CALL_END":
            stats["in"] += getattr(event, "input_tokens", 0) or 0
            stats["out"] += getattr(event, "output_tokens", 0) or 0
        elif kind == "TEXT_BLOCK_DELTA":
            stats["text"].append(getattr(event, "delta", "") or "")

        # 逐字输出不适合打时间线，跳过纯增量事件
        if kind.endswith("_DELTA") and kind != "TEXT_BLOCK_DELTA":
            continue
        if kind == "TEXT_BLOCK_DELTA":
            print(getattr(event, "delta", ""), end="", flush=True)
            continue

        depth = DEPTH.get(kind, 2)
        indent = "  " * depth
        print(f"{elapsed:8.0f}ms  {indent}{kind:<22} {payload(event)}")

    print()
    print("-" * 72)
    print(f"模型调用 {stats['model_calls']} 次｜工具调用 {stats['tool_calls']} 次"
          f"｜token in={stats['in']} out={stats['out']}"
          f"｜总耗时 {(time.perf_counter() - start) * 1000:.0f}ms")


async def main() -> None:
    agent = Agent(
        name="Buddy",
        system_prompt=(
            "你叫 Buddy，是一个住在命令行里的工作助手。"
            "需要用工具获取信息时必须调用工具。回答简短。"
        ),
        model=build_model(),
        toolkit=build_toolkit(),
        react_config=ReActConfig(max_iters=10),  # 最多转 10 轮，防止死循环烧钱
    )

    # 命令行脚本没有确认界面。工具默认会"停下来等人点头"，
    # 在这里就会卡在 REQUIRE_USER_CONFIRM 上。先整体放行，第 7 章再管住它。
    agent.state.permission_context.mode = PermissionMode.BYPASS

    await run_with_trace(
        agent,
        "现在几点？顺便数一下这句话有多少字：手写循环其实不复杂。",
    )


if __name__ == "__main__":
    asyncio.run(main())
