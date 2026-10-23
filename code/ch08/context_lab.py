"""第 8 章实验：上下文压缩到底省了多少 token。

不需要 API key。用 ScriptedModel 驱动同样的工作量，跑两种配置：
  关闭压缩（窗口给到 100 万）vs 开启压缩（窗口 4000，触发线 80%）

运行：python context_lab.py
"""

import asyncio

from agentscope.agent import Agent, ContextConfig
from agentscope.message import UserMsg
from agentscope.permission import PermissionMode
from agentscope.tool import FunctionTool, Toolkit

from fake_model import ScriptedModel

ROUNDS = 6
RESULT_CHARS = 400


async def fake_search(keyword: str) -> str:
    """检索一批资料。

    Args:
        keyword: 检索关键词
    """
    return f"{keyword}：" + "结果内容。" * RESULT_CHARS


async def run(context_size: int, enable_compression: bool, label: str) -> None:
    model = ScriptedModel(context_size=context_size, tool_rounds=ROUNDS)

    context_config = ContextConfig(
        trigger_ratio=0.8,
        reserve_ratio=0.1,
        compression_fallback_to_truncation=enable_compression,
    )

    agent = Agent(
        name="Lab",
        system_prompt="你是检索助手。",
        model=model,
        toolkit=Toolkit(tools=[FunctionTool(fake_search)]),
        context_config=context_config,
    )
    agent.state.permission_context.mode = PermissionMode.BYPASS

    await agent.reply(UserMsg(name="user", content="帮我分六批检索资料，最后汇总。"))

    print(f"\n=== {label} ===")
    print("每次模型调用时的输入 token 数：")
    print("  " + " -> ".join(str(n) for n in model.input_tokens))
    print(f"峰值 {max(model.input_tokens)}　末值 {model.input_tokens[-1]}")
    print(f"上下文消息数 {len(agent.state.context)}　摘要长度 {len(agent.state.summary or '')}")
    if agent.state.summary:
        print("摘要：", agent.state.summary.replace("\n", " ")[:100])


async def main() -> None:
    await run(
        context_size=1_000_000,
        enable_compression=False,
        label="关闭压缩（大窗口）",
    )
    await run(
        context_size=4000,
        enable_compression=True,
        label="开启压缩（4k 窗口，触发线 3200）",
    )


if __name__ == "__main__":
    asyncio.run(main())
