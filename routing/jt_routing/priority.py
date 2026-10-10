"""F1: vulnerability-aware priority and mobility.

V = (1.5·elderly + 2.0·disabled + 1.3·children_u5 + 1.8·pregnant) / population
priority = 0.45·urgency + 0.25·pop_norm + 0.20·V_norm + 0.10·route_risk
"""

from __future__ import annotations

from jt_shared.models import Colony

from . import config


def vulnerability(c: Colony) -> float:
    if c.population_est <= 0:
        return 0.0
    v = c.vulnerable
    raw = sum(w * getattr(v, k) for k, w in config.VULN_WEIGHTS.items())
    return raw / c.population_est


class Normaliser:
    """Normalises population (share of the largest) and vulnerability (min-max) over the seeded
    colonies, so the values are stable across steps and V_norm > 0.6 picks out the most vulnerable."""

    def __init__(self, colonies: list[Colony]):
        self.max_pop = max((c.population_est for c in colonies), default=1) or 1
        vs = [vulnerability(c) for c in colonies] or [0.0]
        self.min_v, self.max_v = min(vs), max(vs)

    def pop_norm(self, c: Colony) -> float:
        return c.population_est / self.max_pop

    def v_norm(self, c: Colony) -> float:
        span = self.max_v - self.min_v
        return 0.0 if span <= 0 else (vulnerability(c) - self.min_v) / span


def urgency(lead_h: float) -> float:
    return min(1.0, max(0.0, 1.0 - lead_h / config.PLAN_HORIZON_H))


def score(lead_h: float, pop_norm: float, v_norm: float, route_risk: float) -> float:
    s = (config.W_URGENCY * urgency(lead_h) + config.W_POP * pop_norm + config.W_VULN * v_norm
         + config.W_RISK * min(1.0, max(0.0, route_risk)))
    return round(min(1.0, max(0.0, s)), 3)


def walk_speed(v_norm: float) -> float:
    return config.SLOW_WALK_SPEED_KMH if v_norm > config.SLOW_V_NORM else config.WALK_SPEED_KMH
