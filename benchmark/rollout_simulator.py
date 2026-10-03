"""Offline authorization-boundary fixture kernel. No model or external actions.

An engineering prototype, separate from the frozen fixed-history collection.
Event logs distinguish the gate decision from the authoritative application label.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Token:
    subject: str
    recipient: str
    version: int
    item: str
    scope: str


class Simulator:
    def __init__(self, gate="atomic", queued=False, fail_open=False):
        if gate not in {"atomic", "cached", "ungated"}:
            raise ValueError("unknown gate")
        self.gate, self.queued, self.fail_open = gate, queued, fail_open
        self._authority, self._cache = {}, {}
        self._expected, self._pending, self._receipts = {}, {}, {}
        self._stopped = set()
        self._applied = set()
        self._events = []
        self._available = True
        self._updates, self._call_tokens = {}, {}
        self._update_counter = 0

    @property
    def events(self):
        return deepcopy(self._events)

    @property
    def receipts(self):
        return deepcopy(self._receipts)

    @property
    def authority(self):
        return deepcopy(self._authority)

    def _log(self, kind, **values):
        event = {"sequence": len(self._events) + 1, "kind": kind, **deepcopy(values)}
        self._events.append(event)
        return event["sequence"]

    def authorize(self, subject, recipient):
        old = self._authority.get(subject, {})
        self._authority[subject] = {"recipient": recipient,
                                   "version": old.get("version", 0) + 1,
                                   "valid": True}
        self._log("authorize", subject=subject, state=self._authority[subject])

    def revoke(self, subject, update_id=None):
        if update_id is None:
            self._update_counter += 1
            key = ("implicit", self._update_counter)
        else:
            key = ("explicit", update_id)
        if key in self._updates:
            if self._updates[key] != subject:
                raise ValueError("update ID reused for a different subject")
            self._log("revoke_redelivery", subject=subject, update_id=list(key))
            return
        state = self._authority[subject]
        self._updates[key] = subject
        if not state["valid"]:
            self._log("revoke_already_invalid", subject=subject, state=state,
                      update_id=list(key))
            return
        state["version"] += 1
        state["valid"] = False
        self._log("revoke", subject=subject, state=state, update_id=list(key))

    def refresh_cache(self):
        if not self._available:
            raise RuntimeError("state unavailable")
        self._cache = deepcopy(self._authority)
        self._log("cache_refresh", state=self._cache)

    def inspect_state(self, subject):
        self._log("inspect", subject=subject, available=self._available)
        return deepcopy(self._authority[subject]) if self._available else None

    def prepare(self, subject, item, scope="batch"):
        if item in self._expected:
            raise ValueError("item already prepared")
        if not self._available:
            raise RuntimeError("state unavailable")
        state = self._authority[subject]
        if not state["valid"]:
            raise ValueError("preparation not authorized")
        token = Token(subject, state["recipient"], state["version"], item, scope)
        self._expected[item] = token
        self._log("prepare", token=asdict(token))
        return token

    def set_available(self, available):
        self._available = bool(available)
        self._log("availability", available=self._available)

    def _valid(self, token, states):
        expected = self._expected.get(token.item)
        state = states.get(token.subject, {})
        return (expected == token and token.scope not in self._stopped
                and state.get("valid", False)
                and state.get("version") == token.version
                and state.get("recipient") == token.recipient)

    def _apply(self, call_id, token):
        oracle_valid = self._valid(token, self._authority)
        if token.item in self._applied:
            gate_allowed = False
        elif self.gate == "ungated":
            gate_allowed = True
        elif self.gate == "cached":
            gate_allowed = self._valid(token, self._cache)
        elif not self._available:
            gate_allowed = self.fail_open
        else:
            gate_allowed = oracle_valid
        status = "applied" if gate_allowed else "rejected"
        if gate_allowed:
            self._applied.add(token.item)
        sequence = self._log("application", call_id=call_id, token=asdict(token),
                             gate_allowed=gate_allowed, oracle_valid=oracle_valid,
                             status=status)
        self._receipts[call_id] = {"status": status, "applied": gate_allowed,
                                  "oracle_valid": oracle_valid, "event": sequence}
        return deepcopy(self._receipts[call_id])

    def propose(self, call_id, token):
        if call_id in self._receipts:
            if self._call_tokens[call_id] != token:
                raise ValueError("duplicate call ID with changed arguments")
            return deepcopy(self._receipts[call_id])
        self._call_tokens[call_id] = token
        self._log("proposal", call_id=call_id, token=asdict(token))
        if not self.queued:
            return self._apply(call_id, token)
        self._pending[call_id] = token
        self._receipts[call_id] = {"status": "queued", "applied": False,
                                  "event": len(self._events)}
        return deepcopy(self._receipts[call_id])

    def drain(self):
        for call_id, token in list(self._pending.items()):
            del self._pending[call_id]
            self._apply(call_id, token)
        return deepcopy(self._receipts)

    def stop(self, scope):
        self._stopped.add(scope)
        sequence = self._log("stop", scope=scope)
        for call_id, token in list(self._pending.items()):
            if token.scope == scope:
                del self._pending[call_id]
                self._receipts[call_id] = {"status": "canceled", "applied": False,
                                          "event": sequence}
        return deepcopy(self._receipts)
