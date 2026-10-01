from __future__ import annotations


def mount_to_nonebot(runtime) -> None:
    """把 LifeRuntime 挂到 NoneBot 生命周期。

    这个文件是 Life Core 中唯一需要知道 NoneBot 存在的地方之一。
    Kernel / Runtime 本身都不 import NoneBot。
    """

    from nonebot import get_driver

    driver = get_driver()

    @driver.on_startup
    async def _start_life_runtime() -> None:
        await runtime.start()

    @driver.on_shutdown
    async def _stop_life_runtime() -> None:
        await runtime.stop()
