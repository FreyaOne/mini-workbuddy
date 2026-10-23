"""一个不联网的假模型，用于在没有 API key 的情况下演示 Agent 的完整循环。

它只做三件事：
  1. 前 N 轮返回工具调用块
  2. 之后返回一段固定文本
  3. 当收到"请你总结上下文"这类请求时，返回一段固定摘要

第 8 章的 token 曲线实验靠它跑通，不消耗任何 token。
"""

from typing import Any

from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolCallBlock
from agentscope.model import (
    ChatModelBase,
    ChatResponse,
    ChatUsage,
    FinishedReason,
    StructuredResponse,
)

SUMMARY_MARKER = "continuation summary"


class ScriptedModel(ChatModelBase):
    """按剧本回答的模型。

    Args:
        context_size: 假装自己的上下文窗口有多大
        tool_rounds: 前几轮用于发起工具调用
    """

    def __init__(
        self,
        context_size: int = 4000,
        tool_rounds: int = 6,
        tool_name: str = "fake_search",
    ) -> None:
        self.model = "scripted"
        self.stream = False
        self.context_size = context_size
        self.parameters = None
        self.max_retries = 0
        self.retry_delay = 0.0
        self.credential = None
        self.formatter = OpenAIChatFormatter()

        self._round = 0
        self._tool_rounds = tool_rounds
        self._tool_name = tool_name
        self.calls = 0
        self.input_tokens: list[int] = []

    def _is_summary_request(self, messages: list[Msg]) -> bool:
        for msg in messages:
            text = msg.get_text_content() or ""
            if SUMMARY_MARKER in text:
                return True
        return False

    async def __call__(
        self,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.calls += 1
        self.input_tokens.append(await self.count_tokens(messages=messages, tools=tools))

        # 压缩时框架会来要摘要，这里必须返回一段文本，否则框架判定失败并退化为截断
        if self._is_summary_request(messages):
            return self._text_response(
                "已完成前 3 批检索，结果都在第 2 批里；下一步是汇总三批并输出报告。",
            )

        self._round += 1
        if self._round <= self._tool_rounds:
            return ChatResponse(
                content=[
                    ToolCallBlock(
                        type="tool_call",
                        id=f"call_{self._round}",
                        name=self._tool_name,
                        input=f'{{"keyword": "第{self._round}批"}}',
                    ),
                ],
                is_last=True,
                id=f"resp_{self._round}",
                type="chat_response",
                usage=ChatUsage(input_tokens=0, output_tokens=20, time=0.01),
            )

        return self._text_response("检索完成，共三批结果。")

    def _text_response(self, text: str) -> ChatResponse:
        return ChatResponse(
            content=[TextBlock(type="text", text=text)],
            is_last=True,
            id=f"resp_{self.calls}",
            type="chat_response",
            usage=ChatUsage(input_tokens=0, output_tokens=20, time=0.01),
            finished_reason=FinishedReason.COMPLETED,
        )

    async def generate_structured_output(
        self,
        messages: list[Msg],
        structured_model: Any,
        **kwargs: Any,
    ) -> StructuredResponse:
        """压缩上下文时框架走的是这条路，必须返回一份符合 schema 的内容。

        这里返回固定的五段摘要。真实模型会根据 compression_prompt 自己总结。
        """
        self.calls += 1
        self.input_tokens.append(
            await self.count_tokens(messages=messages, tools=None),
        )
        return StructuredResponse(
            content={
                "task_overview": "用户要求分 6 批检索资料，最后汇总成一份结果。",
                "current_state": "已完成前 3 批检索，原始结果分别落在第 1 至第 3 条工具结果里。",
                "important_discoveries": "每批检索结果约 1600 token，逐批累积后上下文增长很快。",
                "next_steps": "继续执行剩余批次，然后汇总输出。",
                "context_to_preserve": "回复用中文，保留具体数字（如批次数量）。",
            },
            id=f"struct_{self.calls}",
            type="structured_response",
            usage=ChatUsage(input_tokens=0, output_tokens=80, time=0.01),
            finished_reason=FinishedReason.COMPLETED,
        )
