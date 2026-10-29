"""第 2 章附件：验证 role 的块类型约束在构造阶段就会被拦下。

运行：python role_rule.py

对应文档 2.3 节。user 角色只能装 TextBlock / DataBlock，
塞进 ToolCallBlock 会在构造消息时就失败，不用等到请求 API 收到 400。
最后一段演示三个工厂函数如何省去手写 role。
"""

from pydantic import ValidationError

from agentscope.message import AssistantMsg, SystemMsg, ToolCallBlock, UserMsg


def demo_role_rule() -> None:
    try:
        UserMsg(
            name="user",
            content=[ToolCallBlock(id="c1", name="Read", input="{}")],
        )
    except ValidationError as exc:
        # Msg 是 pydantic 模型，抛的是 ValidationError，
        # 原始那句 ValueError 文本在 errors()[0]["msg"] 里
        print(f"构造失败：{exc.errors()[0]['msg']}")
        print("→ 错误在本地就被拦下，不用等到请求 API 收到 400。")
    else:
        print("（没有报错：说明当前版本放宽了这条约束）")


def demo_factories() -> None:
    """三个工厂函数：role 由函数名锁死，不用手写。"""
    print()
    print("三个工厂函数：")
    for factory, msg in (
        ("UserMsg", UserMsg(name="user", content="你好")),  # role 自动是 user
        ("AssistantMsg", AssistantMsg(name="Buddy", content="你好呀")),  # role 自动是 assistant
        ("SystemMsg", SystemMsg(name="system", content="你是个助手")),  # role 自动是 system
    ):
        # 三个工厂返回的都是 Msg，区别只在 role 和 content
        print(f"  {factory:<13} role={msg.role!r:<12} text={msg.get_text_content()!r}")


def main() -> None:
    demo_role_rule()
    demo_factories()


if __name__ == "__main__":
    main()


