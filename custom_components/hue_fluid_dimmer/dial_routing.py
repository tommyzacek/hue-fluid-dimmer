"""Controller-local, temporary dial targets; no persistent device state changes."""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class Lease:
    targets: tuple[str, ...]
    deadline: float
    timer: asyncio.TimerHandle | None = None


class DialRouting:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.leases: dict[str, Lease] = {}

    def borrow(self, controller, targets):
        self.expire(controller)
        lease = Lease(tuple(targets), self.clock() + 5)
        self.leases[controller] = lease
        lease.timer = asyncio.get_running_loop().call_later(5, self.expire, controller, lease)

    def motion(self, controller):
        lease = self.leases.get(controller)
        if lease is None:
            return None
        if self.clock() >= lease.deadline:
            self.expire(controller, lease)
            return None
        if lease.timer:
            lease.timer.cancel()
        lease.deadline = self.clock() + 5
        lease.timer = asyncio.get_running_loop().call_later(5, self.expire, controller, lease)
        return lease.targets

    def expire(self, controller, lease=None):
        current = self.leases.get(controller)
        if current is None or (lease is not None and current is not lease):
            return
        self.leases.pop(controller)
        if current.timer:
            current.timer.cancel()

    def close(self):
        for controller in tuple(self.leases):
            self.expire(controller)
