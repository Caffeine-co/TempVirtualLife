from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable

from .derived import derive_state
from .kernel import LifeKernel
from .models import JournalRecord, LifeEvent, LifeState, RuntimeView
from .repository import SQLiteLifeRepository


RuntimeListener = Callable[[RuntimeView, list[JournalRecord]], Awaitable[None] | None]


class LifeRuntime:
    """Kernel 的异步运行容器。

    关键保证：
    - 单写者；
    - copy-on-write；
    - Snapshot + Journal 原子提交；
    - 支持未来事件持久化；
    - 停机后可补算；
    - Host/Adapter 不需要直接接触 Kernel 内部状态。
    """

    def __init__(self, kernel: LifeKernel, repository: SQLiteLifeRepository, clock):
        self.kernel = kernel
        self.repository = repository
        self.clock = clock

        self._state: LifeState | None = None
        self._lock = asyncio.Lock()
        self._wakeup = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running = False
        self._listeners: list[RuntimeListener] = []

    def add_listener(self, listener: RuntimeListener) -> None:
        """监听已成功提交的状态变化；适合以后接 Action Executor / UI。"""

        self._listeners.append(listener)

    async def start(self) -> None:
        if self._running:
            return

        await self.repository.initialize()
        state = await self.repository.load_state()

        if state is None:
            # 冷启动也使用 copy-on-write 语义：先构造，再提交，再发布到内存。
            initial = self.kernel.create_initial_state(self.clock.now())
            records = self.kernel.initialize(initial)
            initial.revision = 1
            await self.repository.commit(initial, records)
            self._state = initial
        else:
            self._state = state

        # 启动时处理停机期间已到期的未来事件，并补算到真实现在。
        await self.sync()

        self._running = True
        self._task = asyncio.create_task(self._background_loop(), name="life-runtime")

    async def stop(self) -> None:
        if not self._running:
            return

        await self.sync()
        self._running = False
        self._wakeup.set()

        if self._task is not None:
            await self._task
            self._task = None

    async def sync(self) -> LifeState:
        """把状态推进到 clock.now()，同时按时间顺序消费到期 future events。"""

        notification = None
        async with self._lock:
            current = self._require_state()
            now = self.clock.now()
            if now < current.as_of:
                raise ValueError(
                    f"Clock 比生命状态更早: clock={now.isoformat()} state={current.as_of.isoformat()}"
                )

            due = await self.repository.due_events(now)
            if now == current.as_of and not due:
                return current.model_copy(deep=True)

            working = current.model_copy(deep=True)
            records: list[JournalRecord] = []
            consumed: list[int] = []

            for pending_id, event in due:
                if event.occurred_at < working.as_of:
                    records.append(
                        JournalRecord(
                            occurred_at=working.as_of,
                            kind="late_scheduled_event_applied",
                            data={
                                "event_type": event.type,
                                "original_time": event.occurred_at.isoformat(),
                            },
                        )
                    )
                else:
                    records.extend(self.kernel.advance_to(working, event.occurred_at))
                records.extend(self.kernel.handle_event(working, event))
                consumed.append(pending_id)

            if working.as_of < now:
                records.extend(self.kernel.advance_to(working, now))

            notification = await self._commit_working(working, records, consumed)
            result = self._require_state().model_copy(deep=True)

        # Listener 永远在写锁外执行，允许 Adapter 在回调中再次 get_state/submit。
        await self._notify(notification)
        return result

    async def submit(self, event: LifeEvent) -> LifeState:
        """提交外部事件。

        未来事件会进入持久化 pending queue；已经发生的事件立即作用。
        """

        now = self.clock.now()
        if event.occurred_at > now:
            await self.repository.schedule_event(event)
            self._wakeup.set()
            return await self.get_state()

        notification = None
        async with self._lock:
            current = self._require_state()
            working = current.model_copy(deep=True)
            records: list[JournalRecord] = []

            if event.occurred_at < working.as_of:
                records.append(
                    JournalRecord(
                        occurred_at=working.as_of,
                        kind="late_event_applied",
                        data={
                            "event_type": event.type,
                            "original_time": event.occurred_at.isoformat(),
                        },
                    )
                )
            else:
                records.extend(self.kernel.advance_to(working, event.occurred_at))

            records.extend(self.kernel.handle_event(working, event))

            if working.as_of < now:
                records.extend(self.kernel.advance_to(working, now))

            notification = await self._commit_working(working, records, [])
            result = self._require_state().model_copy(deep=True)

        self._wakeup.set()
        await self._notify(notification)
        return result

    async def get_state(self) -> LifeState:
        async with self._lock:
            return self._require_state().model_copy(deep=True)

    async def get_view(self) -> RuntimeView:
        async with self._lock:
            state = self._require_state().model_copy(deep=True)
            return RuntimeView(
                state=state,
                perception=self.kernel.perception.frame(state),
                derived=derive_state(state),
            )

    async def _commit_working(
        self,
        working: LifeState,
        records: list[JournalRecord],
        consumed_pending_ids: list[int],
    ):
        """Copy-on-write 的真正提交点。

        在 repository.commit 成功前，self._state 仍然保持旧对象，因此磁盘异常不会
        让内存状态先走到一个无法恢复的 revision。
        """

        old = self._require_state()
        working.revision = old.revision + 1
        await self.repository.commit(
            working,
            records,
            consumed_pending_ids=consumed_pending_ids,
        )
        self._state = working

        if not records or not self._listeners:
            return None

        view = RuntimeView(
            state=working.model_copy(deep=True),
            perception=self.kernel.perception.frame(working),
            derived=derive_state(working),
        )
        # 返回不可变通知数据；真正回调由 sync/submit 在释放锁之后执行。
        return view, list(records)

    async def _notify(self, notification) -> None:
        if notification is None:
            return
        view, records = notification
        for listener in list(self._listeners):
            try:
                result = listener(view, records)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                # UI/Adapter 故障不能反向破坏已经提交成功的生命状态。
                continue

    async def _background_loop(self) -> None:
        while self._running:
            self._wakeup.clear()

            async with self._lock:
                state = self._require_state()
                internal_time = self.kernel.next_wakeup_time(state)
                now = self.clock.now()

            pending_time = await self.repository.next_pending_time()
            candidates = [t for t in (internal_time, pending_time) if t is not None]

            if not candidates:
                timeout = 3600.0
            else:
                next_time = min(candidates)
                timeout = max(0.0, (next_time - now).total_seconds())

            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                await self.sync()

    def _require_state(self) -> LifeState:
        if self._state is None:
            raise RuntimeError("LifeRuntime 尚未 start()")
        return self._state
