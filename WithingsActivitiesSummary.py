import pandas as pd
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

CSV_SOUBOR = "activities.csv"
CSV_STEPS  = "aggregates_steps.csv"
VYSTUP_STACKED = "stacked_chart.png"
VYSTUP_SORTED = "sorted_chart.png"

def safe_parse_json(s):
    if s is None:
        return None
    if isinstance(s, float) and pd.isna(s):
        return None
    s_str = str(s).strip()
    if not s_str:
        return None
    try:
        return json.loads(s_str)
    except Exception:
        try:
            return json.loads(s_str.replace('""', '"'))
        except Exception:
            return None

def to_float_or_none(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def extract_distance(row):
    gps = safe_parse_json(row.get("GPS"))
    data = safe_parse_json(row.get("Data"))
    if isinstance(gps, dict):
        d = to_float_or_none(gps.get("distance"))
        if d is not None:
            return d
    if isinstance(data, dict):
        d = to_float_or_none(data.get("distance"))
        if d is not None:
            return d
    return 0.0

def decimal_hours_to_hm(time_float: float) -> str:
    hours = int(time_float)
    minutes = round((time_float - hours) * 60)
    if minutes != 0 and hours != 0:
      return f"{hours}h {minutes:02d}m"
    elif hours != 0:
      return f"{hours}h"
    elif minutes != 0:
      return f"{minutes}min"
    else:
      return ""  
          
df = pd.read_csv(CSV_SOUBOR, sep=',')
df["from_dt"] = pd.to_datetime(df["from"], errors="coerce", utc=True)
df["to_dt"] = pd.to_datetime(df["to"], errors="coerce", utc=True)
df = df.dropna(subset=["from_dt", "to_dt"])
df["year"] = df["from_dt"].dt.year.astype(int)
df["activity"] = df["Activity type"].astype(str)
df = df[df["activity"] != "Multi Sport"]
df["distance_km"] = df.apply(extract_distance, axis=1) / 1000.0
df["duration_h"] = (df["to_dt"] - df["from_dt"]).dt.total_seconds() / 3600.0
df["duration_h"] = df["duration_h"].clip(lower=0)

pivot = df.pivot_table(index="year", columns="activity",
                       values="distance_km", aggfunc="sum", fill_value=0).sort_index()

last_year = int(df["year"].max())
last_dist = df[df["year"] == last_year].groupby("activity")["distance_km"].sum()
last_dur  = df[df["year"] == last_year].groupby("activity")["duration_h"].sum()
last_cnt  = df[df["year"] == last_year].groupby("activity").size()
total_km_last  = float(last_dist.sum())
total_h_last   = float(last_dur.sum())
total_cnt_last = int(last_cnt.sum())

dfs = pd.read_csv(CSV_STEPS, sep=',')
dfs["date_dt"] = pd.to_datetime(dfs["date"], errors="coerce", yearfirst=True)
dfs_latest_year = dfs[dfs["date_dt"].dt.year == last_year]
last_steps = dfs_latest_year["value"].sum()
last_steps_f = f"{last_steps:,}".replace(",", " ")
     
label_map = {}
for act in pivot.columns:
    d = float(last_dist.get(act, 0.0))
    h = float(last_dur.get(act, 0.0))
    c = int(last_cnt.get(act, 0))
    if d != 0 and h != 0:
        label_map[act] = f"{act} ({c}x, {d:.1f}km, {decimal_hours_to_hm(h)})"
    elif d != 0 and h == 0:     
        label_map[act] = f"{act} ({c}x, {d:.1f}km)"
    elif d == 0 and h != 0:
        label_map[act] = f"{act} ({c}x, {decimal_hours_to_hm(h)})"
    else:
        label_map[act] = act

pivot_renamed = pivot.copy()
pivot_renamed.columns = [label_map.get(c, c) for c in pivot.columns]

plt.figure(figsize=(12, 6))
ax = pivot_renamed.plot(kind="bar", stacked=True, colormap="tab20")
plt.title("Year Activity (agg)", fontsize=14)
plt.xlabel("Year", fontsize=12)
plt.ylabel("Distance (km)", fontsize=12)

handles, labels = ax.get_legend_handles_labels()
virtual_handles = [Patch(facecolor='none', edgecolor='none'),
                   Patch(facecolor='none', edgecolor='none'),
                   Patch(facecolor='none', edgecolor='none'),
                   Patch(facecolor='none', edgecolor='none'),
                   Patch(facecolor='none', edgecolor='none')]
virtual_labels  = [f"Year {last_year} TOTALS :",
                   f" - activities: {total_cnt_last}",
                   f" - active distance: {total_km_last:.2f}km",
                   f" - active time: {decimal_hours_to_hm(total_h_last)}",
                   f" - steps: {last_steps_f}"]

print(f"Year {last_year} TOTALS :")
print(f" - activities: {total_cnt_last}")
print(f" - active distance: {total_km_last:.2f}km")
print(f" - active time: {decimal_hours_to_hm(total_h_last)}")
print(f" - steps: {last_steps_f}")

ax.legend(handles + virtual_handles, labels + virtual_labels,
          title=f"Activities (Year {last_year})", bbox_to_anchor=(1.02, 1),
          fontsize=9,
          loc="upper left", borderaxespad=0.)
plt.tight_layout()
plt.savefig(VYSTUP_STACKED, dpi=150)
plt.close()

totals_sorted = (
    df.groupby(["year", "activity"], as_index=False)["distance_km"]
      .sum()
      .sort_values(by=["year", "distance_km"], ascending=[True, False])
)

years = totals_sorted["year"].unique()
fig, axes = plt.subplots(len(years), 1, figsize=(10, 5 * len(years)))
if len(years) == 1:
    axes = [axes]
for ax, year in zip(axes, years):
    data_year = totals_sorted[totals_sorted["year"] == year]
    ax.barh(data_year["activity"], data_year["distance_km"], color="skyblue")
    ax.set_title(f"Year {year} – Distance by Activity (Sorted)", fontsize=14)
    ax.set_xlabel("Distance (km)", fontsize=12)
    ax.invert_yaxis()
    for i, v in enumerate(data_year["distance_km"]):
        ax.text(v + 0.1, i, f"{v:.2f} km", va="center")
plt.tight_layout()
plt.savefig(VYSTUP_SORTED, dpi=150)
plt.close()

