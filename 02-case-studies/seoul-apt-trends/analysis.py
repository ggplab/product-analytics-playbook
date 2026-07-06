#!/usr/bin/env python3
"""서울 아파트 실거래 전처리 + 핵심 분석 + 차트 생성.

data/apt_trades_raw.csv (fetch_data.py 결과물, 있으면 우선 사용) 또는
data/sample_apt_trades.csv (번들 샘플, fallback) 를 읽어
assets/ 에 PNG 4장을 저장한다.

전처리 파이프라인:
  1. 전용면적(㎡) → 평 환산 (÷ 3.3)
  2. 전용면적 기준 평형대 분류 (소형 ≤60㎡ / 중형 ≤85㎡ / 중대형 ≤102㎡ / 대형)
  3. 계약년월 + 계약일 → 날짜(datetime)
  4. 평당금액 계산 = 거래금액(만원) ÷ 평
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# 한글 라벨 깨짐 방지 (macOS 기준)
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
DATA_CANDIDATES = [ROOT / "data" / "apt_trades_raw.csv", ROOT / "data" / "sample_apt_trades.csv"]
ASSETS = ROOT / "assets"

# ---- 팔레트 (dataviz 스킬 검증된 값 — references/palette.md) ----
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

BLUE = "#2a78d6"
# 순차(sequential) 램프: 낮은 값 → 옅음, 높은 값 → 짙음 (100~600 step)
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]
# 범주형(categorical) 고정 순서: 평형대 4종
TYPE_ORDER = ["소형", "중형", "중대형", "대형"]
CATEGORICAL = {"소형": "#2a78d6", "중형": "#1baf7a", "중대형": "#eda100", "대형": "#008300"}


def category(m2: float) -> str:
    if m2 <= 60:
        return "소형"
    elif m2 <= 85:
        return "중형"
    elif m2 <= 102:
        return "중대형"
    return "대형"


def load_data() -> pd.DataFrame:
    path = next((p for p in DATA_CANDIDATES if p.exists()), None)
    if path is None:
        sys.exit(
            "data/ 에 CSV가 없습니다. python fetch_data.py 로 데이터를 받거나, "
            "저장소에 포함된 data/sample_apt_trades.csv 가 있는지 확인하세요."
        )
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"계약년월": str, "계약일": str})
    print(f"[load] {path.name} — {len(df):,}건")
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["거래금액(만원)", "전용면적(㎡)"]).copy()
    df["평"] = (df["전용면적(㎡)"].astype(float) / 3.3).round(2)
    df["유형"] = df["전용면적(㎡)"].astype(float).apply(category)
    df["계약일자"] = pd.to_datetime(
        df["계약년월"].str.zfill(6) + df["계약일"].astype(str).str.zfill(2),
        format="%Y%m%d",
    )
    df["평당금액"] = (df["거래금액(만원)"].astype(float) / df["평"]).round(2)
    print(f"[preprocess] 완료 — {len(df):,}건, 기간 {df['계약일자'].min().date()} ~ {df['계약일자'].max().date()}")
    return df


def style_axes(ax, y_grid=True):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    if y_grid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)


def chart_monthly_trend(df: pd.DataFrame):
    """1) 월별 거래량 & 중위 평당금액 추이 — 축이 다른 두 지표는 2단 패널로 분리(dual-axis 금지)."""
    monthly = df.groupby(df["계약일자"].dt.to_period("M")).agg(
        거래량=("평당금액", "size"), 중위평당금액=("평당금액", "median")
    )
    labels = [str(p) for p in monthly.index]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, facecolor=SURFACE)
    fig.suptitle("월별 거래량 & 중위 평당금액 추이", fontsize=13, color=INK_PRIMARY, fontweight="bold")

    ax1.set_facecolor(SURFACE)
    ax1.bar(labels, monthly["거래량"], color=BLUE, width=0.6, zorder=2)
    ax1.set_ylabel("거래량 (건)", color=INK_SECONDARY, fontsize=9)
    style_axes(ax1)

    ax2.set_facecolor(SURFACE)
    ax2.plot(labels, monthly["중위평당금액"], color=BLUE, linewidth=2, marker="o", markersize=4, zorder=2)
    ax2.set_ylabel("중위 평당금액 (만원/평)", color=INK_SECONDARY, fontsize=9)
    style_axes(ax2)
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = ASSETS / "01_monthly_trend.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[chart] {out.name} 저장")


def chart_gu_ranking(df: pd.DataFrame):
    """2) 자치구별 평당금액 랭킹 — 크기 비교이므로 순차(sequential) 단일 색상 램프."""
    ranked = df.groupby("구")["평당금액"].median().sort_values(ascending=True)

    lo, hi = ranked.min(), ranked.max()

    def to_ramp_color(v):
        idx = int((v - lo) / (hi - lo) * (len(BLUE_RAMP) - 1)) if hi > lo else len(BLUE_RAMP) - 1
        return BLUE_RAMP[max(0, min(idx, len(BLUE_RAMP) - 1))]

    colors = [to_ramp_color(v) for v in ranked.values]

    fig, ax = plt.subplots(figsize=(8, 9), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.barh(ranked.index, ranked.values, color=colors, zorder=2)
    for bar, v in zip(bars, ranked.values):
        ax.text(v + hi * 0.01, bar.get_y() + bar.get_height() / 2, f"{v:,.0f}",
                va="center", fontsize=8, color=INK_SECONDARY)
    ax.set_xlabel("중위 평당금액 (만원/평)", color=INK_SECONDARY, fontsize=9)
    ax.set_title("자치구별 평당금액 랭킹 (중위값)", fontsize=13, color=INK_PRIMARY, fontweight="bold", pad=12)
    style_axes(ax, y_grid=False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    out = ASSETS / "02_gu_ranking.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[chart] {out.name} 저장")


def chart_size_distribution(df: pd.DataFrame):
    """3) 평형대별 평당금액 분포 — 범주(4종)는 고정 순서 categorical 색상."""
    data = [df.loc[df["유형"] == t, "평당금액"].values for t in TYPE_ORDER]

    fig, ax = plt.subplots(figsize=(7, 5.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    bp = ax.boxplot(data, tick_labels=TYPE_ORDER, patch_artist=True, widths=0.5,
                     medianprops=dict(color=INK_PRIMARY, linewidth=1.5),
                     whiskerprops=dict(color=BASELINE), capprops=dict(color=BASELINE),
                     flierprops=dict(markeredgecolor=INK_MUTED, markersize=3, alpha=0.5))
    for patch, t in zip(bp["boxes"], TYPE_ORDER):
        patch.set_facecolor(CATEGORICAL[t])
        patch.set_alpha(0.75)
        patch.set_edgecolor(CATEGORICAL[t])

    ax.set_ylabel("평당금액 (만원/평)", color=INK_SECONDARY, fontsize=9)
    ax.set_title("평형대별 평당금액 분포", fontsize=13, color=INK_PRIMARY, fontweight="bold", pad=12)
    style_axes(ax)

    fig.tight_layout()
    out = ASSETS / "03_size_distribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[chart] {out.name} 저장")


def chart_type_share(df: pd.DataFrame):
    """4) 면적 유형별 거래 비중 — part-to-whole은 100% 누적 가로 막대 (파이 대신)."""
    counts = df["유형"].value_counts()
    total = counts.sum()
    shares = [counts.get(t, 0) / total for t in TYPE_ORDER]

    fig, ax = plt.subplots(figsize=(9, 2.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    left = 0.0
    for t, s in zip(TYPE_ORDER, shares):
        ax.barh(0, s, left=left, color=CATEGORICAL[t], height=0.5, label=t, zorder=2)
        if s > 0.03:
            ax.text(left + s / 2, 0, f"{t}\n{s:.0%}", ha="center", va="center",
                    fontsize=9, color="white" if t in ("중대형",) else INK_PRIMARY, fontweight="bold")
        left += s

    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("면적 유형별 거래 비중", fontsize=13, color=INK_PRIMARY, fontweight="bold", pad=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False,
               fontsize=9, labelcolor=INK_SECONDARY)

    fig.tight_layout()
    out = ASSETS / "04_type_share.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[chart] {out.name} 저장")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    df = load_data()
    df = preprocess(df)

    print("\n[핵심 통계]")
    print(f"  전체 거래: {len(df):,}건")
    print(f"  중위 평당금액: {df['평당금액'].median():,.0f}만원/평")
    print(f"  평당금액 최고 자치구: {df.groupby('구')['평당금액'].median().idxmax()}")

    chart_monthly_trend(df)
    chart_gu_ranking(df)
    chart_size_distribution(df)
    chart_type_share(df)

    print(f"\n완료 — {ASSETS} 에 차트 4장 저장됨")


if __name__ == "__main__":
    main()
