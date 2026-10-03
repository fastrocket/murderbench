"""Prospective cap extension; preserves old frozen ledger and all reservations."""
from decimal import Decimal
import json
from benchmark.necessity_native import Ledger, ROOT, amount, canonical, RESERVE


class AuthorizedLedger(Ledger):
    def __init__(self, path, group, baseline=None):
        authorization = json.loads((ROOT/"plans/budget-authorization-2026-10-03.json").read_text())
        if authorization["lifetime_cap_usd"] != "100" or authorization["additional_authorized_usd"] != "50":
            raise ValueError("authorization changed")
        if not group or any(c not in "0123456789abcdef" for c in group):
            raise ValueError("hexadecimal budget group required")
        options = {"study_cap":Decimal("50")}
        if baseline is not None:
            options["baseline"] = baseline
        super().__init__(path, **options)
        self.group, self.lifetime_cap = group, Decimal("100")

    def reserve(self, call_id, study, payload):
        if not study.startswith(self.group+"/"):
            raise ValueError("outside authorized pilot budget group")
        packet = canonical(payload)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT study,payload,state,response FROM calls WHERE id=?", (call_id,)).fetchone()
            if row:
                if row[0] != study or row[1] != packet:
                    raise RuntimeError("saved call identity/payload mismatch")
                if row[2] != "received":
                    raise RuntimeError("unresolved request; never retry automatically")
                self.conn.execute("COMMIT")
                return json.loads(row[3])
            if self.conn.execute("SELECT 1 FROM calls WHERE study=? AND state!='received' LIMIT 1", (study,)).fetchone():
                raise RuntimeError("unresolved study reservation")
            rows = self.conn.execute("SELECT study,amount FROM calls").fetchall()
            total = sum((amount(r[1]) for r in rows), Decimal(0))
            pilot = sum((amount(r[1]) for r in rows if r[0].startswith(self.group+"/")), Decimal(0))
            if amount(self.baseline())+total+RESERVE > self.lifetime_cap or pilot+RESERVE > Decimal("50"):
                raise RuntimeError("budget admission rejected before request")
            self.conn.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?)",
                              (call_id,study,packet,"reserved",str(RESERVE),None,None))
            self.conn.execute("COMMIT")
            return None
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

    def summary(self):
        result = super().summary()
        result["authorized_lifetime_cap_usd"] = str(self.lifetime_cap)
        result["remaining_accounted_usd"] = str(max(Decimal(0), self.lifetime_cap-amount(result["lifetime_accounted_usd"])))
        pilot = sum((amount(r[0]) for r in self.conn.execute("SELECT amount FROM calls WHERE study LIKE ?", (self.group+"/%",))), Decimal(0))
        result["pilot_accounted_usd"] = str(pilot)
        return result
