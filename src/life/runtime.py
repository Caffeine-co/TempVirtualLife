from __future__ import annotations

import asyncio
from datetime import datetime

from .derived import derive_state
from .kernel import LifeKernel
from .models import (
    CharacterRuntimeState,
    JournalRecord,
    LifeEvent,
    RuntimeView,
)
from .repository import SQLiteLifeRepository


class LifeRuntime:
    """Kernel 的运行容器。

    负责：
    1. 单写者锁
    2. 持久化
    3. 后台唤醒
    4. 从停机时间补算到现在

    不负责具体角色逻辑。
    """

    def __init__(
        self,
        kernel: LifeKernel,
        repository: SQLiteLifeRepository,
        clock,
    ):
        self.kernel = kernel
        self.repository = repository
        self.clock = clock

        self._state: CharacterRuntimeState | None = None
        self._lock = asyncio.Lock()
        self._wakeup = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        await self.repository.initialize()
        state = await self.repository.load_state()

        if state is None:
            state = CharacterRuntimeState(as_of=self.clock.now())
            records = self.kernel.initialize(state)
            state.revision = 1
            await self.repository.commit(state, records)

        self._state = state
        await self.sync()

        self._running = True
        self._task = asyncio.create_task(
            self._background_loop(),
            name="life-runtime",
        )

    async def stop(self) -> None:
        if not self._running:
            return

        # 最后先结算到当前时刻，再停止后台等待。
        await self.sync()
        self._running = False
        self._wakeup.set()

        if self._task:
            await self._task
            self._task = None

    async def sync(self) -> CharacterRuntimeState:
        """把角色状态推进到 clock.now()。"""

        async with self._lock:
            state = self._require_state()
            now = self.clock.now()
            if now < state.as_of:
                raise ValueError(
                    f"Clock 比状态时间更早: clock={now.isoformat()} state={state.as_of.isoformat()}"
                )
            if now == state.as_of:
                return state.model_copy(deep=True)

            records = self.kernel.advance_to(state, now)
            await self._commit(records)
            return state.model_copy(deep=True)

    async def submit(self, event: LifeEvent) -> CharacterRuntimeState:
        """提交一个离散事件。

        所有外部模块都应该通过这里影响角色，而不是直接修改 state。
        """

        async with self._lock:
            state = self._require_state()
            now = self.clock.now()
            if event.occurred_at > now:
                raise ValueError("当前版本不接受发生在未来的外部事件")

            records: list[JournalRecord] = []

            if event.occurred_at < state.as_of:
                # 第一版不做历史回滚。迟到事件在当前状态上生效，并留下明确日志。
                records.append(
                    JournalRecord(
                        occurred_at=state.as_of,
                        kind="late_event_applied",
                        data={
                            "event_type": event.type,
                            "original_time": event.occurred_at.isoformat(),
                        },
                    )
                )
            else:
                records.extend(self.kernel.advance_to(state, event.occurred_at))

            records.extend(self.kernel.handle_event(state, event))

            # 事件处理后再补到真实当前时间，确保调用返回时状态就是“现在”。
            if state.as_of < now:
                records.extend(self.kernel.advance_to(state, now))

            await self._commit(records)

        # 外部事件可能改变下一个内部唤醒时刻。
        self._wakeup.set()
        return state.model_copy(deep=True)

    async def get_state(self) -> CharacterRuntimeState:
        async with self._lock:
            return self._require_state().model_copy(deep=True)

    async def get_view(self) -> RuntimeView:
        async with self._lock:
            state = self._require_state().model_copy(deep=True)
            return RuntimeView(state=state, derived=derive_state(state))

    async def _commit(self, records: list[JournalRecord]) -> None:
        state = self._require_state()
        state.revision += 1
        await self.repository.commit(state, records)

    async def _background_loop(self) -> None:
        """睡到最近的行为结束/日程边界；外部事件会提前唤醒。"""

        while self._running:
            self._wakeup.clear()

            async with self._lock:
                state = self._require_state()
                next_time = self.kernel.next_wakeup_time(state)
                now = self.clock.now()

            if next_time is None:
                # 理论上只要有 action 就不会走到这里；保留一个低频保险。
                timeout = 3600.0
            else:
                timeout = max(0.0, (next_time - now).total_seconds())

            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                await self.sync()

    def _require_state(self) -> CharacterRuntimeState:
        if self._state is None:
            raise RuntimeError("LifeRuntime 尚未 start()")
        return self._state
