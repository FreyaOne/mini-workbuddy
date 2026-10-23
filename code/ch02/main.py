"""第 2 章：一个 40 行的事件探测器。

它不关心模型回答了什么，只关心「这一轮里发生了什么」。
第 12 章的前端会用到同一套事件，所以这份代码不是玩具。
"""

import asyncio
import os

from dotenv import load_dotenv

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.message import UserMsg
from agentscope.model import OpenAIChatModel

load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def build_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=API_KEY, base_url=BASE_URL or None),
        model=MODEL_NAME,
    )


def describe(event) -> str:
    """从事件里挑出最值得看的一个字段。"""
    # 事件对象上常见字段：delta / tool_call_name / state / finished_reason
    for field in ("delta", "tool_call_name", "state", "finished_reason"):
        value = getattr(event, field, None)
        if value is not None:
            return f"{field}={value!r}"
    return ""


async def main() -> None:
    agent = Agent(
        name="Buddy",
        system_prompt="你叫 Buddy，回答简短。",
        model=build_model(),
    )

    print("=" * 62)
    print("事件流开始")
    print("=" * 62)

    # reply_stream 是异步生成器：模型吐出一点，我们就能看到一点
    # 注意：enumerate 只认同步可迭代对象，异步生成器要自己数
    i = 0
    async for event in agent.reply_stream(
        UserMsg(name="user", content="用一句话说明什么是异步编程"),
    ):
        kind = event.type.value  # 事件的种类，字符串
        print(f"[{i:02d}] {kind:<22} {describe(event)}")
        i += 1

    print("=" * 62)
    print("事件流结束")


if __name__ == "__main__":
    asyncio.run(main())
