"""Independent extension checks; leave the instructor's tests unchanged.

Run: python -m missions.check_extensions
"""
from math import isclose
from missions.m2_inference_levers import reasoning_budget, run
from missions.carbon_scheduling import run as carbon_run
from finops.sustainability import wh_per_query


def main():
    def row(reasoning):
        return dict(is_reasoning=reasoning, input_tokens=800, output_tokens=200,
                    route_tier='large', cached_input_tokens=400, is_batch=1)
    low = reasoning_budget([row(1)] + [row(0)] * 19)
    assert low['disabled_requests'] == 0
    assert isclose(low['before_wh'], low['after_wh'])
    high = reasoning_budget([row(1)] * 10)
    assert high['after_reasoning_requests'] == 1
    assert high['disabled_requests'] == 9
    assert isclose(high['before_wh'] - high['after_wh'], 9 * (wh_per_query(1000, is_reasoning=True) - wh_per_query(1000)))
    assert high['before_usd'] == high['after_usd']
    assert reasoning_budget([])['before_wh'] == 0
    assert reasoning_budget([row(1)], cap=1)['disabled_requests'] == 0
    try:
        reasoning_budget([], cap=1.1)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid cap accepted')
    stages = list(run(False)['stages_daily'].values())
    assert all(a >= b for a, b in zip(stages, stages[1:]))
    assert isclose(sum(a-b for a,b in zip(stages, stages[1:])), stages[0]-stages[-1])
    carbon = carbon_run()
    assert carbon['cleanest'] == 'europe-north1'
    assert carbon['cheapest'] == 'us-east-wa'
    assert isclose(sum(j['before_g'] for j in carbon['jobs']), carbon['before_g'])
    assert isclose(sum(j['after_g'] for j in carbon['jobs']), carbon['after_g'])
    assert isclose(carbon['after_g'] / carbon['before_g'], 30 / 380)
    llm = next(j for j in carbon['jobs'] if j['job_id'] == 'job-train-llm')
    assert llm['gpu_hours'] == 20 * 14 * 8  # actual days, not a 30-day extrapolation
    assert llm['wh'] == llm['gpu_hours'] * 700
    print('Extension checks passed: caps, unchanged USD, energy, breakdown, fixed-work carbon.')


if __name__ == '__main__':
    main()
