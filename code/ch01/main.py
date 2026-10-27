"""第 1 章：让 mini-workbuddy 开口说第一句话。

这一章只做一件事：创建一个 Agent，然后和它聊几轮。
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

# 配置：全部从环境变量读，别写死在代码里。换模型只改 .env，代码一行不动。
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # 留空则走 OpenAI 官方地址
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PROMPT = "> "
EXIT_WORDS = {"/exit", "/quit", "exit", "quit", "q"}


def build_model() -> OpenAIChatModel:
    """造一个模型实例。后面每一章都复用它。"""
    return OpenAIChatModel(
        credential=OpenAICredential(
            api_key=API_KEY,
            base_url=BASE_URL or None,
        ),
        model=MODEL_NAME,
    )


async def chat_loop(agent: Agent) -> None:
    """读一行 -> 问一句 -> 打一句，直到你说退出。

    这个 while 循环是本文件唯一"多余"的东西，但它换来两件事：
    1. 你可以连着问，像真的在用一个助手，而不是跑一次脚本看一行输出；
    2. 你会亲眼看到"对话是有记忆的"——历史存在 Agent 对象里，
       每次 reply() 都会把之前几轮一起带进模型，所以第二句里的"它"它听得懂。
    """
    while True:
        # Ctrl+C 和 Ctrl+D（管道结束）都当作"我要走了"，而不是抛一堆堆栈
        try:
            text = input(PROMPT).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n（已退出）")
            return

        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            print("（已退出）")
            return

        try:
            # reply 内部会跑完整个「推理-行动」循环，返回最终消息
            reply = await agent.reply(UserMsg(name="user", content=text))
            print(reply.get_text_content())
        except Exception as exc:  # noqa: BLE001
            # 网络抖动、key 过期、额度用光——都只影响这一轮，不该把整个会话打死。
            # 第 13 章会把这里换成框架自带的错误对象。
            print(f"[出错] {type(exc).__name__}: {exc}")
            print("  先查 .env 里的 BASE_URL 与 MODEL 是否配对，常见错误见 1.5 节。")


async def main() -> None:
    agent = Agent(
        name="Buddy",  # 它自己的名字，会出现在消息的 name 字段里
        system_prompt=(
            "你叫 Buddy，是一个住在命令行里的工作助手。"
            "说话直接、简短，不超过两句话。"
        ),
        model=build_model(),
    )

    print("Buddy 已就位（第 1 章版本：还没有工具，只能聊天。输入 /exit 退出）")
    await chat_loop(agent)


if __name__ == "__main__":
    # except Exception 抓不到 KeyboardInterrupt（它是 BaseException），
    # 所以"模型正在输出时按 Ctrl+C"要在这里接住，否则会弹一堆堆栈。
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n（已中断）")
