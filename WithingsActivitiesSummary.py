'''
# Withings Activities Summary Graphs
Python script to sum and show activities summary from Withings raw data (csv)

## How-To
- Request for data export from your [Withings profile](https://app.withings.com)
- Wait for download link
- Download ZIP archive and extract to "data" folder
- Run  WithingsActivitiesSummary.py

## Licence
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

(c)2025 Petr Klosko
'''
import pandas as pd
import json
import sys
import subprocess
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import calendar

CSV_SOUBOR = "data/activities.csv"
CSV_STEPS  = "data/aggregates_steps.csv"
VYSTUP_STACKED = "stacked_chart.png"
VYSTUP_STACKED_MONTHLY = "stacked_chart_monthly.png"
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

def openFile(path):
    imgViewer = {'linux':'xgd-open',
                 'win32':'explorer',
                 'darwin':'open'}[sys.platform]
    subprocess.Popen([imgViewer, path])            

args = [a.strip().lower() for a in sys.argv[1:] if a.strip()]
       
df = pd.read_csv(CSV_SOUBOR, sep=',')
df["from_dt"] = pd.to_datetime(df["from"], errors="coerce", utc=True)
df["to_dt"] = pd.to_datetime(df["to"], errors="coerce", utc=True)
df = df.dropna(subset=["from_dt", "to_dt"])
df["year"] = df["from_dt"].dt.year.astype(int)
df["activity"] = df["Activity type"].astype(str)
if args:
  target_activity = args[0]
  df = df[df["activity"].str.lower() == target_activity]
else:
  target_activity = ""
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
plt.title(f"Year Activity (agg) {target_activity}", fontsize=14)
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
plt.savefig(f"{target_activity}{last_year}-{VYSTUP_STACKED}", dpi=150)
plt.close()

#last year monthly
df_last_year = df[df["year"] == last_year].copy()
df_last_year["month"] = df_last_year["from_dt"].dt.month
monthly_pivot = df_last_year.pivot_table(index="month", columns="activity",
                       values="distance_km", aggfunc="sum", fill_value=0).sort_index()
monthly_pivot_renamed = monthly_pivot.copy()
monthly_pivot_renamed.columns = [label_map.get(c, c) for c in monthly_pivot.columns]
month_labels = [calendar.month_abbr[m] for m in monthly_pivot_renamed.index]

plt.figure(figsize=(12, 6))
ax2 = monthly_pivot_renamed.plot(kind="bar", stacked=True, colormap="tab20")
ax2.set_title(f"Activity {target_activity} in {last_year}", fontsize=14)
ax2.set_xlabel("Month", fontsize=10)
ax2.set_ylabel("Distance (km)", fontsize=10)
ax2.set_xticklabels(month_labels)
for lbl in ax2.get_xticklabels():
  lbl.set_rotation(0)
  lbl.set_fontsize(5)

handles2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(handles2 + virtual_handles, labels2 + virtual_labels,
          title=f"Year {last_year} activities", bbox_to_anchor=(1.02, 1),
          fontsize=9,
          loc="upper left", borderaxespad=0.)
plt.tight_layout()
plt.savefig(f"{target_activity}{last_year}-{VYSTUP_STACKED_MONTHLY}", dpi=150)
plt.close()
openFile(f"{target_activity}{last_year}-{VYSTUP_STACKED_MONTHLY}")

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
    ax.set_title(f"Year {year} – Distance by Activity (Sorted {target_activity})", fontsize=14)
    ax.set_xlabel("Distance (km)", fontsize=12)
    ax.invert_yaxis()
    for i, v in enumerate(data_year["distance_km"]):
        ax.text(v + 0.1, i, f"{v:.2f} km", va="center")
plt.tight_layout()
plt.savefig(f"{target_activity}{last_year}-{VYSTUP_SORTED}", dpi=150)
plt.close()

