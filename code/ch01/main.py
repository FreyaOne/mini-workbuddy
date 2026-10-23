"""第 1 章：让 mini-workbuddy 开口说第一句话。

这一章只做一件事：创建一个 Agent，发一条消息，把回答打印出来。
比上一章多了什么：没有上一章，这是起点。
"""

import asyncio
import os

from dotenv import load_dotenv

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.message import UserMsg
from agentscope.model import OpenAIChatModel

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# 配置：全部从环境变量读，别写死在代码里
# 换模型只改 .env，一行代码都不用动
# ---------------------------------------------------------------------------
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # 留空则走 OpenAI 官方地址
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def build_model() -> OpenAIChatModel:
    """造一个模型实例。后面每一章都复用它。"""
    return OpenAIChatModel(
        credential=OpenAICredential(
            api_key=API_KEY,
            base_url=BASE_URL or None,
        ),
        model=MODEL_NAME,
    )


async def main() -> None:
    agent = Agent(
        name="Buddy",  # 它自己的名字，会出现在消息的 name 字段里
        system_prompt=(
            "你叫 Buddy，是一个住在命令行里的工作助手。"
            "说话直接、简短，不超过两句话。"
        ),
        model=build_model(),
    )

    user_msg = UserMsg(name="user", content="你好，你是谁？")

    # reply 内部会跑完整个「推理-行动」循环，返回最终消息
    reply = await agent.reply(user_msg)

    print(reply.get_text_content())


if __name__ == "__main__":
    asyncio.run(main())
