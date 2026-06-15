"""GPU Credit System — see problem.md.

API:
    add_credit(credit_id, amount, timestamp, expiration) -> None
    subtract(amount, timestamp) -> None
    get_balance(timestamp) -> int | None

Hints (don't peek if you want a cold attempt):
- Events arrive out of order → store a flat event log, replay on each query.
- Drain order at subtract time: grants expiring soonest first.
- get_balance returns None in two distinct cases — read problem.md.
"""

from __future__ import annotations

import heapq

import counter


class GPUCredit:
    def __init__(self) -> None:
        #(timestamp, event, event_obj)
        self.events = []

    def add_credit(
        self,
        credit_id: str,
        amount: int,
        timestamp: int,
        expiration: int,
    ) -> None:
        self.events.append((timestamp, 'add', (credit_id, amount, timestamp, expiration)))

    def subtract(self, amount: int, timestamp: int) -> None:
        self.events.append((timestamp, 'subtract', (amount, timestamp)))

    def get_balance(self, timestamp: int) -> int | None:
        #name: (start, end, counter)
        grants = {}
        has_active = False
        # order of events, created in real-timeo
        next_grants = []
        balance = 0

        for ts, event, obj in sorted(self.events, key = lambda x : x[0]):
            if ts > timestamp:
                break
            if event == 'add' :
                credit_id, amount, timestamp, expiration = obj
                grants[credit_id] = (timestamp, timestamp + expiration, amount)
                balance += amount
                heapq.heappush(next_grants, (timestamp + expiration, credit_id))
                if timestamp + expiration > ts:
                    has_active = True
            elif event == 'subtract':
                amount, _ = obj
                #fetch next available grant
                while amount > 0 and heapq:
                    end, credit_id = heapq.heappop(next_grants)
                    take = min(grants[credit_id][2], amount)
                    grants[credit_id][2] -= take
                    balance -= take
                    amount -= take
                    if grants[credit_id][2] > 0 :
                        heapq.heappush(next_grants, (end, credit_id))
                    if amount == 0:
                        break
                #if you cant fully drain
                balance -= amount
        if not has_active or balance < 0 :
            return None
        return balance
