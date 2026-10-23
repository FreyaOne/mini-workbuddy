"""第 12 章：同一套后端，换一张脸。

后端逻辑一行没改——直接复用第 11 章的 FastAPI 应用，
只把静态目录从 `ch11/static` 换成 `ch12/` 整个目录。

启动：
    python main.py
    # 没有可用 key 时先跑假事件流：
    MOCK=1 python main.py
    然后打开 http://127.0.0.1:8000/

想直接看界面长什么样、又不想起服务：
    用浏览器打开 mock.html（?scene=stream / tool / error / task）
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

# 把第 11 章的目录放进搜索路径，复用它的 runtime.py 与 main.py
sys.path.insert(0, str(HERE.parent / "ch11"))

import main as ch11  # noqa: E402  第 11 章的 app / 路由 / 构建函数

from fastapi.staticfiles import StaticFiles  # noqa: E402

app = ch11.app

# 第 11 章在 "/" 上挂了它自己的验证页；本章要把根路径让给真正的界面，
# 所以先摘掉那条路由，再把整个目录挂到 "/" 上。
app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/"]
app.mount("/", StaticFiles(directory=str(HERE), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(__import__("os").getenv("PORT", "8000")))
