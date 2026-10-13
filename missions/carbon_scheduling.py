"""Extension 5: fixed work, actual job days, catalog watts, no cloud API."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, catalog_by_type, num
from finops import sustainability as s


def run() -> dict:
    cat = catalog_by_type()
    cleanest = min(s.REGION_CARBON, key=s.REGION_CARBON.get)
    cheapest = min(s.REGION_PRICE_KWH, key=s.REGION_PRICE_KWH.get)
    jobs = []
    for j in load_csv("workloads.csv"):
        if not int(num(j["interruptible"])):
            continue
        hours = num(j["hours_per_day"]) * num(j["days"]) * num(j["num_gpus"])
        wh = hours * num(cat[j["gpu_type"]]["watts"])
        jobs.append(dict(job_id=j["job_id"], gpu_hours=hours, wh=wh,
                         before_g=s.carbon_g(wh, "us-east-1"),
                         after_g=s.carbon_g(wh, cleanest)))
    total_wh = sum(j["wh"] for j in jobs)
    regions = [dict(region=region, price_kwh=s.REGION_PRICE_KWH[region],
                    carbon_kwh=s.REGION_CARBON[region],
                    electricity_usd=s.energy_cost_usd(total_wh, region),
                    carbon_g=s.carbon_g(total_wh, region)) for region in s.REGION_CARBON]
    return dict(jobs=jobs, regions=regions, total_wh=total_wh,
                cleanest=cleanest, cheapest=cheapest,
                before_g=s.carbon_g(total_wh, "us-east-1"),
                after_g=s.carbon_g(total_wh, cleanest))


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
