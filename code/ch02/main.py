"""第 2 章：读懂一次对话。

本章，我们要一起来做两件事：看清一条消息的结构，看懂一次回复的过程
"""

# asyncio：Python 标准库的异步运行时，用来驱动协程（async/await）
import asyncio
# os：读取环境变量（API Key、Base URL、模型名）
import os
# sys：用于自定义 unraisablehook，过滤 httpcore 的清理噪音
import sys

# load_dotenv：把 .env 文件里的变量加载进 os.environ
from dotenv import load_dotenv

# Agent：本章的主角，负责「收消息 -> 调模型 -> 产出事件」
from agentscope.agent import Agent
# OpenAICredential：模型调用的凭证（api_key / base_url）
from agentscope.credential import OpenAICredential
# UserMsg：一条「用户消息」，是 Agent 的输入
from agentscope.message import UserMsg
# OpenAIChatModel：兼容 OpenAI 协议的聊天模型封装
from agentscope.model import OpenAIChatModel

# override=True 表示 .env 里的值优先于系统已有环境变量
load_dotenv(override=True)

# 从环境变量读取配置，读不到时给一个兜底默认值
API_KEY = os.getenv("OPENAI_API_KEY", "")  # 必填：模型服务的密钥
BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # 可选：自定义网关/代理地址
MODEL_NAME = os.getenv("OPENAI_MODEL", "")  # 模型名称


# ---------- 过滤 httpcore 异步生成器清理噪音 ----------
# 这段代码忽略，主要是兼容不同的python版本，无实际意义
def _silence_httpcore_asyncgen_error(unraisable):
    """只忽略 httpcore 在异步生成器终结时抛出的已知噪音，其余照常打印。"""
    exc = unraisable.exc_value
    if isinstance(exc, RuntimeError) and "generator didn't stop after athrow()" in str(exc):
        return  # 静默忽略这条已知噪音
    sys.__unraisablehook__(unraisable)  # 其他不可用异常按默认方式报告


sys.unraisablehook = _silence_httpcore_asyncgen_error
# -------------------------------------------------------


def build_model() -> OpenAIChatModel:
    """构造一个模型客户端。

    base_url 为空时传 None，让 SDK 使用官方默认地址。
    """
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=API_KEY, base_url=BASE_URL or None),
        model=MODEL_NAME,
    )


def describe(event) -> str:
    """从事件里挑出最值得看的一个字段。

    事件流里会夹杂很多种事件，这里只做「一事件一行」的简略展示：
    按优先级依次尝试几个常见字段，命中第一个非空值就返回。
    """
    # 事件对象上常见字段：delta / tool_call_name / state / finished_reason
    for field in ("delta", "tool_call_name", "state", "finished_reason"):
        value = getattr(event, field, None)  # 字段可能不存在，用 getattr 兜底
        if value is not None:
            return f"{field}={value!r}"  # !r 走 repr，方便看清字符串边界
    return ""  # 没有任何可展示字段时返回空串


async def main() -> None:
    # 组装 Agent：名字 + 人设（system prompt）+ 模型
    agent = Agent(
        name="Buddy",
        system_prompt="你叫 Buddy，回答简短。",
        model=build_model(),
    )

    # 打印分隔线，方便肉眼区分输出的开始与结束
    print("=" * 62)
    print("事件流开始")
    print("=" * 62)

    # 先拿到异步生成器对象，便于在 finally 里显式关闭
    stream = agent.reply_stream(
        UserMsg(name="user", content="用一句话说明什么是异步编程"),
    )

    # 注意：enumerate 只认同步可迭代对象，异步生成器要自己数
    i = 0
    try:
        # async for：逐个消费 Agent 产出的事件（文本增量、工具调用、结束原因等）
        async for event in stream:
            kind = event.type.value  # 事件的种类，字符串
            # i 是序号，kind 左对齐占 22 列，describe 给出该事件的关键信息
            print(f"[{i:02d}] {kind:<22} {describe(event)}")
            i += 1  # 异步生成器不能配 enumerate，手动递增
    finally:
        # 显式关闭异步生成器：让底层 HTTP 流按正确路径收尾，避免 GC 时跨任务清理报错
        await stream.aclose()

    print("=" * 62)
    print("事件流结束")


if __name__ == "__main__":
    # asyncio.run：创建事件循环并执行 main 协程，直到它结束
    asyncio.run(main())