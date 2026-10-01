from __future__ import annotations

import asyncio

from .config import load_life_config
from .factory import build_life_runtime


async def main() -> None:
    config = load_life_config("life.example.json")
    runtime = build_life_runtime(config)
    await runtime.start()

    view = await runtime.get_view()
    print(view.model_dump_json(indent=2))
    print("LifeRuntime 已启动。Ctrl+C 结束。")

    try:
        await asyncio.Event().wait()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
