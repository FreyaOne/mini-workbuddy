"""第 9 章：状态往返验证。

存成 JSON，再读回来，看消息、任务清单、结构化输出 schema 是不是原样还在。

    cd code/ch09 && python verify_roundtrip.py
"""

import asyncio
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agentscope.message import UserMsg                        # noqa: E402
from agentscope.state import AgentState                       # noqa: E402
from agentscope.tool import TaskCreate                        # noqa: E402

from store import JsonStateStore                              # noqa: E402


async def main() -> None:
    root = HERE / "sandbox" / "_verify_sessions"
    shutil.rmtree(root, ignore_errors=True)
    store = JsonStateStore(str(root))

    state = AgentState()
    state.context.append(UserMsg(name="user", content="记住：我的周报固定分三段"))
    await TaskCreate().call(_agent_state=state, subject="写进度", description="本周完成项")
    await TaskCreate().call(_agent_state=state, subject="写问题", description="阻塞项")
    state.reply_context.structured_schema = {"type": "object", "properties": {}}

    store.save("mu", "buddy", state)
    print("saved files:", sorted(p.name for p in (root / "mu" / "buddy").iterdir()))

    back = store.load("mu", "buddy", state.session_id)
    print("restored msg:", len(back.context), "tasks:", [t.subject for t in back.tasks_context.tasks])
    print("structured_schema after load:", back.reply_context.structured_schema)

    print("list:", store.list_sessions("mu", "buddy"))
    print("size:", (root / "mu" / "buddy" / f"{state.session_id}.json").stat().st_size)
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
