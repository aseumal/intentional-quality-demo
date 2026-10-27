"""VRTQ: Value, Risk, Time, Quality. Intention, written down.

Weights and tiers are the tester's judgment, made explicit so a machine can
apply them and a human can challenge them.
"""
from dataclasses import dataclass

WEIGHTS = {"V": 0.30, "R": 0.35, "T": 0.20, "Q": 0.15}
P1, P2 = 7.0, 4.5

# Value: business impact if this function is wrong (0-10). Set by humans, on purpose.
FUNCTION_VALUE = {"discount": 9, "shipping_fee": 7, "loyalty_points": 4}


@dataclass
class VRTQScore:
    V: float
    R: float
    T: float
    Q: float

    @property
    def total(self):
        return round(sum(WEIGHTS[k] * getattr(self, k) for k in WEIGHTS), 2)

    @property
    def tier(self):
        t = self.total
        return "P1" if t >= P1 else ("P2" if t >= P2 else "P3")


def score_gap(mutant, evidence) -> VRTQScore:
    """Score a surviving mutant that the debate ruled a real gap."""
    V = FUNCTION_VALUE.get(mutant.function, 5)
    # Risk: boundary changes on the main business rule are the classic production bug.
    x = evidence["input"]
    first = x[0] if isinstance(x, (list, tuple)) else x
    if mutant.operator == "relational" and first not in (0, 0.0):
        R = 9
    else:
        R = 4  # edge input (zero value order) is rarer in production
    if first in (0, 0.0):
        V = min(V, 5)  # a PHP 0 order (full voucher) matters less than a real sale
    T = 9  # a single unit test: cheap to add and to run
    Q = 9 if evidence.get("counterexample") else 5  # confidence: we hold a concrete failing input
    return VRTQScore(V, R, T, Q)
