import json, sys
with open("ml/artifacts/candidate0_metrics.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)
print("C0 overall_mae={:.4f}".format(d["overall_mae"]))
h = d.get("metrics_by_horizon", {})
for k, v in h.items():
    print("  {}: mae={:.2f}  cov={:.1f}%  winkler={:.2f}".format(
        k, v["mae_railtwin"], v["coverage_80_percent"], v["winkler_score"]))
