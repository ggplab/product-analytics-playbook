"""
Equipment Sensor Analysis — ML 없이 groupby로 하는 이상탐지
============================================================
목적 → 가설 → 검증 → 해석 구조로 진행하는 경량 분석 레시피.

머신러닝(분류 모델, 회귀)을 전혀 쓰지 않고, pandas의 groupby·개수 세기·비율
계산만으로 "장비가 고장 나기 전에 미리 알 수 있는가"에 답한다.

실행:
    uv venv .venv && source .venv/bin/activate
    uv pip install -r requirements.txt
    python analysis.py

결과: assets/ 폴더에 PNG 차트 3장 저장.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

# ── 한글 폰트 설정 (macOS 기준) ────────────────────────────────────────────────
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, 'data', 'equipment_anomaly_data.csv')
ASSET_DIR = os.path.join(BASE, 'assets')
os.makedirs(ASSET_DIR, exist_ok=True)

# ── 색상 (dataviz 스킬 팔레트 — 상태 색상은 categorical과 분리) ──────────────────
NORMAL   = '#2a78d6'   # categorical slot 1 (blue) — "정상" 식별자
FAULT    = '#d03b3b'   # status: critical — "고장" 상태
GOOD     = '#0ca30c'   # status: good
WARNING  = '#fab219'   # status: warning
CRITICAL = '#d03b3b'   # status: critical
SURFACE  = '#fcfcfb'   # light chart surface

# 시퀀셜 블루 램프(단일 hue, light→dark) — 히트맵용
SEQ_BLUE = LinearSegmentedColormap.from_list(
    'seq_blue', ['#cde2fb', '#6da7ec', '#2a78d6', '#184f95', '#0d366b']
)

# ── 데이터 로드 ────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
df['faulty'] = df['faulty'].astype(int)

total = len(df)
fault_total = df['faulty'].sum()
normal_total = total - fault_total
fault_rate = fault_total / total * 100

print(f"전체 행수: {total}")
print(f"고장(faulty=1): {fault_total}건 ({fault_rate:.1f}%)")
print(f"정상(faulty=0): {normal_total}건")

normal_df = df[df['faulty'] == 0]
fault_df = df[df['faulty'] == 1]

print("\n[센서별 정상 vs 고장 평균 — groupby 없이 mean()만으로 비교]")
for col in ['temperature', 'pressure', 'vibration', 'humidity']:
    nm = normal_df[col].mean()
    fm = fault_df[col].mean()
    print(f"  {col:12s} 정상 {nm:.3f} / 고장 {fm:.3f} / 차이 {fm - nm:+.3f}")


def save(fig, name):
    path = os.path.join(ASSET_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=SURFACE)
    plt.close(fig)
    print(f"  저장: {path}")


# ══════════════════════════════════════════════════════════════════════════
# 가설 1 — 진동이 심한 장비일수록 고장이 많다
# ══════════════════════════════════════════════════════════════════════════
print("\n[가설 1] 진동 vs 고장 여부")

fig, axes = plt.subplots(1, 2, figsize=(10, 5), facecolor=SURFACE)

ax = axes[0]
bins = np.linspace(df['vibration'].min(), df['vibration'].max(), 35)
ax.hist(normal_df['vibration'], bins=bins, alpha=0.7, color=NORMAL,
        label='정상', edgecolor='white', linewidth=0.5)
ax.hist(fault_df['vibration'], bins=bins, alpha=0.7, color=FAULT,
        label='고장', edgecolor='white', linewidth=0.5)
ax.axvline(fault_df['vibration'].mean(), color=FAULT, linestyle='--', linewidth=1.5,
           label=f'고장 평균 {fault_df["vibration"].mean():.2f}')
ax.axvline(normal_df['vibration'].mean(), color=NORMAL, linestyle='--', linewidth=1.5,
           label=f'정상 평균 {normal_df["vibration"].mean():.2f}')
ax.set_xlabel('진동 수치')
ax.set_ylabel('장비 수(건)')
ax.set_title('진동 분포: 정상 vs 고장')
ax.set_facecolor(SURFACE)
ax.legend(fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax2 = axes[1]
labels = ['정상', '고장']
means = [normal_df['vibration'].mean(), fault_df['vibration'].mean()]
bars = ax2.bar(labels, means, color=[NORMAL, FAULT], width=0.45, edgecolor='white')
for bar, val in zip(bars, means):
    ax2.text(bar.get_x() + bar.get_width() / 2, val + 0.03, f'{val:.2f}',
              ha='center', va='bottom', fontweight='bold')
ax2.set_ylabel('진동 평균')
ax2.set_title('그룹별 진동 평균 비교 (groupby 없이 mean만으로)')
ax2.set_facecolor(SURFACE)
ax2.set_ylim(0, max(means) * 1.25)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

plt.tight_layout()
save(fig, '01_vibration_distribution.png')

# ══════════════════════════════════════════════════════════════════════════
# 가설 2 — 진동과 온도가 동시에 높으면 고장률이 훨씬 높다 (교호작용)
# ══════════════════════════════════════════════════════════════════════════
print("\n[가설 2] 진동×온도 구간별 고장률 (2차원 groupby)")

vib_bins = [df['vibration'].min(), 1.0, 1.5, 2.0, 2.5, 3.0, df['vibration'].max()]
vib_labels = ['~1.0', '1.0~1.5', '1.5~2.0', '2.0~2.5', '2.5~3.0', '3.0~']
temp_bins = [df['temperature'].min(), 60, 80, 100, 120, df['temperature'].max()]
temp_labels = ['~60°C', '60~80°C', '80~100°C', '100~120°C', '120°C~']

df['vib_bin'] = pd.cut(df['vibration'], bins=vib_bins, labels=vib_labels, include_lowest=True)
df['temp_bin'] = pd.cut(df['temperature'], bins=temp_bins, labels=temp_labels, include_lowest=True)

pivot = df.groupby(['vib_bin', 'temp_bin'], observed=True).agg(
    total=('faulty', 'count'),
    faults=('faulty', 'sum'),
).reset_index()
pivot['rate'] = pivot['faults'] / pivot['total'] * 100

rate_matrix = pivot.pivot(index='vib_bin', columns='temp_bin', values='rate')
count_matrix = pivot.pivot(index='vib_bin', columns='temp_bin', values='total')

fig, ax = plt.subplots(figsize=(10, 5), facecolor=SURFACE)
im = ax.imshow(rate_matrix.values, cmap=SEQ_BLUE, aspect='auto', vmin=0, vmax=60)
plt.colorbar(im, ax=ax, label='고장률(%)', shrink=0.85)

ax.set_xticks(range(len(rate_matrix.columns)))
ax.set_xticklabels(rate_matrix.columns, fontsize=10)
ax.set_yticks(range(len(rate_matrix.index)))
ax.set_yticklabels(rate_matrix.index, fontsize=10)
ax.set_xlabel('온도 구간', fontsize=11)
ax.set_ylabel('진동 구간', fontsize=11)
ax.set_title('진동×온도 구간별 고장률(%) — 진할수록 위험', fontsize=13)

for i in range(rate_matrix.shape[0]):
    for j in range(rate_matrix.shape[1]):
        val = rate_matrix.values[i, j]
        cnt = count_matrix.values[i, j]
        if not np.isnan(val):
            text_color = 'white' if val > 35 else '#1f2933'
            ax.text(j, i, f'{val:.0f}%\n(n={int(cnt)})',
                    ha='center', va='center', fontsize=8.5, color=text_color)

plt.tight_layout()
save(fig, '02_vibration_temperature_heatmap.png')

# ══════════════════════════════════════════════════════════════════════════
# 가설 3 — 진동 임계값 하나로 경보선을 그으면 실제로 쓸만한가
# ══════════════════════════════════════════════════════════════════════════
print("\n[가설 3] 경보선 설정 — 진동 임계값별 고장률 + 정밀도/재현율")

alert_bins = [df['vibration'].min(), 1.5, 2.0, 2.5, 2.6, 3.0, df['vibration'].max()]
alert_labels = ['~1.5', '1.5~2.0', '2.0~2.5', '2.5~2.6', '2.6~3.0', '3.0~']
df['alert_bin'] = pd.cut(df['vibration'], bins=alert_bins, labels=alert_labels, include_lowest=True)

alert_stats = df.groupby('alert_bin', observed=True).agg(
    total=('faulty', 'count'),
    faults=('faulty', 'sum'),
).reset_index()
alert_stats['rate'] = alert_stats['faults'] / alert_stats['total'] * 100

THRESHOLD = 2.6
alarm_df = df[df['vibration'] >= THRESHOLD]
alarm_total = len(alarm_df)
alarm_fault = alarm_df['faulty'].sum()
precision = alarm_fault / alarm_total * 100 if alarm_total > 0 else 0
recall = alarm_fault / fault_total * 100

print(f"  경보선 진동 ≥ {THRESHOLD}")
print(f"  알람 울린 장비: {alarm_total}건 / 그 중 실제 고장: {alarm_fault}건")
print(f"  정밀도(알람 중 실제 고장 비율): {precision:.1f}%")
print(f"  재현율(전체 고장 중 알람으로 잡아낸 비율): {recall:.1f}%")

fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor=SURFACE)

ax = axes[0]
bar_colors = [GOOD if r < 20 else (WARNING if r < 50 else CRITICAL) for r in alert_stats['rate']]
bars = ax.bar(alert_stats['alert_bin'], alert_stats['rate'], color=bar_colors,
              edgecolor='white', width=0.6)
ax.axhline(fault_rate, color='#64748b', linestyle=':', linewidth=1.5,
           label=f'전체 평균 {fault_rate:.1f}%')
ax.axvline(x=3.5, color=FAULT, linestyle='--', linewidth=2, label='경보선 (진동 2.6)')
for bar, val in zip(bars, alert_stats['rate']):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.5, f'{val:.0f}%',
            ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_xlabel('진동 구간')
ax.set_ylabel('고장률(%)')
ax.set_title('진동 구간별 고장률 — 경보선 설정')
ax.set_facecolor(SURFACE)
ax.legend(fontsize=10)
ax.set_ylim(0, max(alert_stats['rate']) * 1.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax2 = axes[1]
metrics = ['알람 중\n실제 고장 비율', '전체 고장 중\n알람으로 잡아낸 비율']
values = [precision, recall]
bars2 = ax2.barh(metrics, values, color=[FAULT, NORMAL], height=0.45, edgecolor='white')
for bar, val in zip(bars2, values):
    ax2.text(val + 0.5, bar.get_y() + bar.get_height() / 2, f'{val:.1f}%',
              va='center', fontsize=13, fontweight='bold')
ax2.set_xlim(0, 110)
ax2.set_xlabel('비율(%)')
ax2.set_title(f'경보선(진동≥{THRESHOLD}) 성능 확인')
ax2.set_facecolor(SURFACE)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

plt.tight_layout()
save(fig, '03_alert_threshold_performance.png')

# ══════════════════════════════════════════════════════════════════════════
# 최종 수치 요약 (README 작성용)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("최종 수치 요약")
print("=" * 60)
print(f"전체: {total}건, 고장: {fault_total}건({fault_rate:.1f}%)")
print(f"경보선(진동≥{THRESHOLD}): 알람 {alarm_total}건 → 정밀도 {precision:.1f}% / 재현율 {recall:.1f}%")
print("\n생성된 차트:")
for f in sorted(os.listdir(ASSET_DIR)):
    print(f"  assets/{f}")
