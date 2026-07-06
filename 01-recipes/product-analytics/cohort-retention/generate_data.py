"""
SaaS 월별 코호트 리텐션 분석용 합성 데이터 생성기.

가상의 B2B SaaS 제품을 가정해, 유저별 가입월(cohort)과 이후 매월 활동 여부를
시뮬레이션한 뒤 단일 CSV(long format)로 저장한다.

설계 포인트 (해석 과제로 활용):
- 플랜(free/starter/pro/enterprise)이 높을수록 월간 리텐션이 높음 — 뚜렷한 계단형 차이
- paid_search 채널은 가입 후 6개월 시점부터 리텐션이 추가로 꺾임 (초기 유입 품질 이슈 가정)
- 2024-05 코호트는 가입 1개월 차에 리텐션이 급락 (특정 월 온보딩 이슈를 가정한 이상치 주입)

재현성: numpy Generator(seed=42) 고정. 파라미터는 상단 상수로 노출되어 있어
값을 바꾸면 다른 패턴의 데이터를 재생성할 수 있다.

실행:
    python generate_data.py
    → data/cohort_activity.csv 생성 (user_id, signup_month, plan, channel, activity_month)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ========== 파라미터 ==========
SEED = 42
N_USERS = 2500

# 월별 코호트: 2024-01 ~ 2024-09 (9개 코호트)
COHORT_MONTHS = pd.period_range("2024-01", "2024-09", freq="M")
# 관측 종료 시점: 2025-03 (가장 이른 코호트 기준 14개월 관측)
OBSERVATION_END = pd.Period("2025-03", freq="M")

PLANS = [("free", 0.60), ("starter", 0.22), ("pro", 0.13), ("enterprise", 0.05)]
CHANNELS = [("organic", 0.35), ("paid_search", 0.30), ("referral", 0.20), ("content", 0.15)]

# 플랜별 월간 리텐션 하자드(그 달까지 살아남았다면, 다음 달에도 남아있을 확률)
BASE_MONTHLY_RETENTION = {
    "free": 0.72,
    "starter": 0.85,
    "pro": 0.90,
    "enterprise": 0.95,
}

# 채널별 리텐션 보정 계수 (organic 기준)
CHANNEL_MULTIPLIER = {
    "organic": 1.00,
    "referral": 1.05,
    "content": 0.98,
    "paid_search": 0.90,
}

# 이상치 주입 1: paid_search 채널은 가입 6개월 차부터 리텐션이 추가로 하락
PAID_SEARCH_LONG_TERM_OFFSET = 6
PAID_SEARCH_LONG_TERM_PENALTY = 0.85

# 이상치 주입 2: 특정 코호트(2024-05)는 1개월 차 리텐션이 급락
ANOMALY_COHORT = pd.Period("2024-05", freq="M")
ANOMALY_OFFSET = 1
ANOMALY_PENALTY = 0.45


def weighted_choice(rng, weighted_items, size):
    items = [item for item, _ in weighted_items]
    weights = np.array([w for _, w in weighted_items])
    weights = weights / weights.sum()
    return rng.choice(items, size=size, p=weights)


def monthly_retention(plan, channel, cohort_month, month_offset):
    """month_offset(0=가입월) → (offset-1)월에서 offset월로 넘어갈 하자드."""
    hazard = BASE_MONTHLY_RETENTION[plan] * CHANNEL_MULTIPLIER[channel]

    if channel == "paid_search" and month_offset >= PAID_SEARCH_LONG_TERM_OFFSET:
        hazard *= PAID_SEARCH_LONG_TERM_PENALTY

    if cohort_month == ANOMALY_COHORT and month_offset == ANOMALY_OFFSET:
        hazard *= ANOMALY_PENALTY

    return float(np.clip(hazard, 0.01, 0.99))


def simulate_user_activity(rng, user_id, signup_month, plan, channel):
    """유저 1명의 (user_id, signup_month, plan, channel, activity_month) 행 리스트.

    Month 0(가입월)은 무조건 활성으로 간주. 이후 매월 하자드에 따라 생존 여부를
    베르누이 시행하고, 한 번 이탈하면 다시 돌아오지 않는다고 가정한다(표준
    로고 리텐션 커브 가정).
    """
    rows = [(user_id, str(signup_month), plan, channel, str(signup_month))]

    month_offset = 1
    current_month = signup_month + 1
    while current_month <= OBSERVATION_END:
        p_retain = monthly_retention(plan, channel, signup_month, month_offset)
        if rng.random() > p_retain:
            break
        rows.append((user_id, str(signup_month), plan, channel, str(current_month)))
        current_month += 1
        month_offset += 1

    return rows


def generate():
    rng = np.random.default_rng(SEED)

    user_ids = np.arange(1, N_USERS + 1)
    signup_months = rng.choice(COHORT_MONTHS, size=N_USERS)
    plans = weighted_choice(rng, PLANS, N_USERS)
    channels = weighted_choice(rng, CHANNELS, N_USERS)

    all_rows = []
    for uid, signup_month, plan, channel in zip(user_ids, signup_months, plans, channels):
        all_rows.extend(
            simulate_user_activity(rng, int(uid), pd.Period(signup_month, freq="M"), plan, channel)
        )

    df = pd.DataFrame(
        all_rows,
        columns=["user_id", "signup_month", "plan", "channel", "activity_month"],
    )
    return df


def print_summary(df):
    n_users = df["user_id"].nunique()
    print(f"Users: {n_users}")
    print(f"Activity rows: {len(df)}")
    print("Plan distribution:")
    print(df.drop_duplicates("user_id")["plan"].value_counts().to_string())
    print("Channel distribution:")
    print(df.drop_duplicates("user_id")["channel"].value_counts().to_string())
    print("Cohort sizes (signup_month):")
    print(df.drop_duplicates("user_id")["signup_month"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    df = generate()
    print_summary(df)

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "cohort_activity.csv"
    df.to_csv(out_path, index=False)

    print(f"\nWritten: {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
