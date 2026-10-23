"""第 10 章离线演示：不需要 API key。

跑两件事：
  1. 三个中间件同时挂上，看它们在哪些节点被调用
  2. 结构化输出：强制模型返回一份符合 schema 的 JSON

运行：python offline_demo.py
"""

import asyncio
import json
from typing import Any

from pydantic import BaseModel, Field

from agentscope.agent import Agent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolCallBlock, UserMsg
from agentscope.model import (
    ChatModelBase,
    ChatResponse,
    ChatUsage,
    FinishedReason,
)
from agentscope.tool import FunctionTool, Toolkit

from agentscope.permission import PermissionMode

from middlewares import AuditMiddleware, RedactMiddleware, StampMiddleware


# --------------------------------------------------------------------------
# 一个按剧本回答的假模型
# --------------------------------------------------------------------------
class ScriptedModel(ChatModelBase):
    def __init__(self) -> None:
        self.model = "scripted"
        self.stream = False
        self.context_size = 32_000
        self.parameters = None
        self.max_retries = 0
        self.retry_delay = 0.0
        self.credential = None
        self.formatter = OpenAIChatFormatter()
        self.calls = 0

    async def __call__(
        self,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.calls += 1
        names = [t.get("function", {}).get("name") for t in (tools or [])]

        # 第一轮：调用 send_sms，参数里带一个手机号，用来验证脱敏
        if self.calls == 1 and "send_sms" in names:
            return ChatResponse(
                content=[ToolCallBlock(
                    type="tool_call", id="call_1", name="send_sms",
                    input=json.dumps({"phone": "13812345678", "text": "明天九点开会"},
                                     ensure_ascii=False),
                )],
                is_last=True, id="r1", type="chat_response",
                usage=ChatUsage(input_tokens=120, output_tokens=18, time=0.01),
            )

        # 要求结构化输出时，调用框架注入的那个工具
        if "GenerateStructuredOutput" in names:
            schema = next(
                t for t in tools if t["function"]["name"] == "GenerateStructuredOutput"
            )
            props = schema["function"]["parameters"].get("properties", {})
            data: dict[str, Any] = {}
            for key, spec in props.items():
                if spec.get("type") == "array":
                    data[key] = ["周四前完成接口联调", "每周五同步进度"]
                elif spec.get("type") in ("integer", "number"):
                    data[key] = 3
                else:
                    data[key] = "季度复盘会"
            return ChatResponse(
                content=[ToolCallBlock(
                    type="tool_call", id="call_struct",
                    name="GenerateStructuredOutput",
                    input=json.dumps(data, ensure_ascii=False),
                )],
                is_last=True, id="r2", type="chat_response",
                usage=ChatUsage(input_tokens=200, output_tokens=60, time=0.01),
            )

        return ChatResponse(
            content=[TextBlock(type="text", text="短信已发出。")],
            is_last=True, id="r3", type="chat_response",
            usage=ChatUsage(input_tokens=180, output_tokens=12, time=0.01),
            finished_reason=FinishedReason.COMPLETED,
        )


# --------------------------------------------------------------------------
# 业务工具与结构化输出模型
# --------------------------------------------------------------------------
async def send_sms(phone: str, text: str) -> str:
    """给指定手机号发短信。

    Args:
        phone: 手机号
        text: 短信内容
    """
    return f"已发送给 {phone}：{text}"


async def read_file(path: str) -> str:
    """读取一个文本文件。

    Args:
        path: 文件路径
    """
    return f"{path} 的内容"


class MeetingSummary(BaseModel):
    """会议纪要。"""

    title: str = Field(description="会议主题")
    decisions: list[str] = Field(description="达成的决定，每条一句话")
    attendees: int = Field(description="参会人数")


async def demo_middlewares() -> None:
    print("=" * 70)
    print("一、三个中间件同时挂上")
    print("=" * 70)

    audit = AuditMiddleware()
    redact = RedactMiddleware()
    stamp = StampMiddleware(stamp="ch10-demo")

    agent = Agent(
        name="Buddy",
        system_prompt="你是一个通知助手。",
        model=ScriptedModel(),
        toolkit=Toolkit(tools=[FunctionTool(send_sms), FunctionTool(read_file)]),
        middlewares=[redact, audit, stamp],   # 顺序即执行顺序：先脱敏，再审计
    )

    # 演示脱敏，不想被确认框打断，走 BYPASS
    agent.state.permission_context.mode = PermissionMode.BYPASS

    msg = await agent.reply(UserMsg(name="user", content="给 13812345678 发条短信，说明天九点开会"))
    print("回复：", msg.get_text_content())
    print("\n审计记录：")
    print(audit.dump())
    print(f"\n脱敏命中：{redact.hits} 处")
    real_prompt = await agent._get_system_prompt()
    print("实际发给模型的 prompt 末尾：", real_prompt[-30:].replace("\n", " "))


async def demo_structured() -> None:
    print()
    print("=" * 70)
    print("二、强制结构化输出")
    print("=" * 70)

    agent = Agent(
        name="Buddy",
        system_prompt="你是一个会议助手。",
        model=ScriptedModel(),
    )

    msg = await agent.reply(
        UserMsg(name="user", content="把今天的会总结一下"),
        structured_schema=MeetingSummary,
    )

    print("模型说的话：", msg.get_text_content())
    print("结构化结果：", msg.structured_output)
    print("字段类型：", type(msg.structured_output).__name__)

    # 拿回来立刻能当 dict 用，也能再校验成模型
    summary = MeetingSummary(**msg.structured_output)
    print("重新校验后：", summary.title, "| 决定", len(summary.decisions), "条")


async def main() -> None:
    await demo_middlewares()
    await demo_structured()


if __name__ == "__main__":
    asyncio.run(main())
