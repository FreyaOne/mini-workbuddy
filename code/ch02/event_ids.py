"""第 2 章附件：不用 API key，直接看清事件上的 reply_id / block_id。

运行：python event_ids.py

三件事：
  1. 事件上的 id 长什么样：reply_id 一轮一个，block_id 一块一个
  2. 碎片交错到达时，按到达顺序拼接会拼错
  3. 按 block_id 归位，才能拼回正确的两块内容
"""

from agentscope.event import (
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
)

# 真实运行时这些 id 由框架生成（32 位十六进制），这里写死成一眼能区分的短串
REPLY_ID = "reply_0001"
BLOCK_A = "block_AAAA"
BLOCK_B = "block_BBBB"


def show(event) -> None:
    """一行打印一个事件：类型 + 它带的 id + 内容。"""
    kind = event.type.value
    block_id = getattr(event, "block_id", "-")  # REPLY_START 没有 block_id
    delta = getattr(event, "delta", "")
    print(f"{kind:<20} reply_id={event.reply_id:<12} block_id={block_id:<12} {delta}")


def demo_ids() -> None:
    """1. 同一轮回复里，reply_id 不变，block_id 每块一个。"""
    print("=" * 78)
    print("一、事件上的 id：reply_id 一轮一个，block_id 一块一个")
    print("=" * 78)

    events = [
        ReplyStartEvent(session_id="s1", reply_id=REPLY_ID, name="Buddy"),
        # 第一块：思考
        TextBlockStartEvent(reply_id=REPLY_ID, block_id=BLOCK_A),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id=BLOCK_A, delta="先读文件"),
        TextBlockEndEvent(reply_id=REPLY_ID, block_id=BLOCK_A),
        # 第二块：回答
        TextBlockStartEvent(reply_id=REPLY_ID, block_id=BLOCK_B),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id=BLOCK_B, delta="地址是"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id=BLOCK_B, delta="127.0.0.1"),
        TextBlockEndEvent(reply_id=REPLY_ID, block_id=BLOCK_B),
    ]
    for event in events:
        show(event)

    print()
    print("观察两点：")
    print("  · reply_id 全程相同 —— 它们都属于同一轮回复")
    print("  · block_id 中途换了一次 —— 换块了，A 的碎片不能拼进 B")
    print()


def demo_interleave() -> None:
    """2 & 3. 碎片交错到达：按顺序拼会错，按 id 归位才对。"""
    print("=" * 78)
    print("二、碎片交错到达时，为什么必须按 id 归位")
    print("=" * 78)

    # 模拟两个块并发输出，碎片按「到达顺序」交错
    arrivals = [
        (BLOCK_A, "文件A第一行；"),
        (BLOCK_B, "文件B第一行；"),
        (BLOCK_A, "文件A第二行；"),
        (BLOCK_B, "文件B第二行；"),
    ]
    for block_id, delta in arrivals:
        show(TextBlockDeltaEvent(reply_id=REPLY_ID, block_id=block_id, delta=delta))

    print()
    print("如果按到达顺序直接拼接：")
    naive = "".join(delta for _, delta in arrivals)
    print(f"  {naive}")
    print("  → 两块内容混在一起，A 的卡片里出现了 B 的文字。")
    print()

    print("如果按 block_id 归位：")
    buckets: dict[str, list[str]] = {}
    for block_id, delta in arrivals:
        buckets.setdefault(block_id, []).append(delta)  # 按 id 分桶，不看到达顺序
    for block_id, parts in buckets.items():
        print(f"  {block_id} -> {''.join(parts)}")
    print("  → 每块都完整且干净。")
    print()

    print("这就是前端要遵守的规则：始终按 id 归位，不按到达顺序归位。")
    print("reply_id 同理：上一轮迟到的碎片 reply_id 对不上，直接丢弃即可。")


def main() -> None:
    demo_ids()
    demo_interleave()


if __name__ == "__main__":
    main()
