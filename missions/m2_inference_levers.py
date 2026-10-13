"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def reasoning_budget(rows, cap: float = 0.10) -> dict:
    """Counterfactual cap: keep tokens/model/cache/batch, disable excess reasoning.

    File order selects retained requests; no confidence labels exist in the CSV.
    Pricing has no reasoning surcharge, so this policy saves energy, not USD.
    """
    if not 0 <= cap <= 1:
        raise ValueError("cap must be between 0 and 1")
    groups = {name: dict(requests=0, tokens=0, usd=0.0, wh=0.0)
              for name in ("reasoning", "standard")}
    retained = int(len(rows) * cap)
    seen = 0
    after_wh = 0.0
    for r in rows:
        reasoning = bool(int(num(r["is_reasoning"])))
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        pin, pout = MODEL_PRICES[r["route_tier"]]
        cost = pricing.request_cost(inp, out, pin, pout,
                                    cached_in=int(num(r["cached_input_tokens"])),
                                    batch=bool(int(num(r["is_batch"]))))
        g = groups["reasoning" if reasoning else "standard"]
        g["requests"] += 1
        g["tokens"] += inp + out
        g["usd"] += cost
        g["wh"] += sustainability.wh_per_query(inp + out, is_reasoning=reasoning)
        if reasoning:
            seen += 1
        after_wh += sustainability.wh_per_query(inp + out, is_reasoning=reasoning and seen <= retained)
    before_wh = sum(g["wh"] for g in groups.values())
    if seen <= retained:
        after_wh = before_wh
    cost = sum(g["usd"] for g in groups.values())
    return dict(groups=groups, cap=cap, before_usd=cost, after_usd=cost,
                before_wh=before_wh, after_wh=after_wh,
                disabled_requests=max(0, seen - retained),
                after_reasoning_requests=min(seen, retained))


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = cascade_cost = cache_cost = 0.0
    total_tokens = 0
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        cascade_cost += pricing.request_cost(inp, out, pin, pout)
        cache_cost += pricing.request_cost(inp, out, pin, pout, cached_in=cached)
        opt_cost += pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")
        print(f"sequential USD/day: {base_cost:.6f} -> {cascade_cost:.6f} -> {cache_cost:.6f} -> {opt_cost:.6f}")
        budget = reasoning_budget(rows)
        print(f"reasoning cap 10%: {budget['disabled_requests']} disabled; "
              f"{budget['before_wh']:.2f} -> {budget['after_wh']:.2f} Wh/day; USD unchanged")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "stages_daily": {"baseline": base_cost, "cascade": cascade_cost,
                         "cache": cache_cost, "batch": opt_cost},
        "reasoning_budget": reasoning_budget(rows),
    }


if __name__ == "__main__":
    run()
