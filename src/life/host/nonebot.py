from __future__ import annotations


def mount_to_nonebot(runtime) -> None:
    """让 NoneBot 只负责 Host 生命周期，不侵入 LifeKernel。"""

    # 延迟 import，确保单独运行 Life Core 时不需要安装/初始化 NoneBot。
    from nonebot import get_driver

    driver = get_driver()

    @driver.on_startup
    async def _start_life_runtime() -> None:
        await runtime.start()

    @driver.on_shutdown
    async def _stop_life_runtime() -> None:
        await runtime.stop()
