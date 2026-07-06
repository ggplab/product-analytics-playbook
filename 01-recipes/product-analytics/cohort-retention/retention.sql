-- ============================================================
-- SaaS 월별 코호트 리텐션 분석 (SQL 버전)
-- 데이터: data/cohort_activity.csv (SQLite에 cohort_activity 테이블로 로드)
--   컬럼: user_id, signup_month(YYYY-MM), plan, channel, activity_month(YYYY-MM)
--   한 행 = "이 유저가 이 달에 활동했다"는 기록. 가입월 행도 포함되어 있음.
--
-- 실행 (SQLite CLI):
--   sqlite3 cohort.db
--   .mode csv
--   .import data/cohort_activity.csv cohort_activity
--   .read retention.sql
-- ============================================================

-- ------------------------------------------------------------
-- STEP 0. 월 문자열(YYYY-MM)을 정수 개월수로 변환하는 표현식
--   month_index = 연도*12 + 월  →  두 월의 차이가 곧 경과 개월 수(month_offset)
--   SQLite에는 DATE_DIFF가 없어 문자열을 잘라 계산한다.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- STEP 1. 코호트별 전체 유저 수 (분모)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS cohort_size;
CREATE VIEW cohort_size AS
SELECT
    signup_month,
    COUNT(DISTINCT user_id) AS cohort_users
FROM cohort_activity
GROUP BY signup_month;

-- ------------------------------------------------------------
-- STEP 2. 유저 x 활동월 → 가입 후 경과 개월(month_offset) 계산
-- ------------------------------------------------------------
DROP VIEW IF EXISTS user_month_offset;
CREATE VIEW user_month_offset AS
SELECT
    user_id,
    signup_month,
    activity_month,
    (
        (CAST(substr(activity_month, 1, 4) AS INTEGER) * 12
         + CAST(substr(activity_month, 6, 2) AS INTEGER))
        -
        (CAST(substr(signup_month, 1, 4) AS INTEGER) * 12
         + CAST(substr(signup_month, 6, 2) AS INTEGER))
    ) AS month_offset
FROM cohort_activity;

-- ------------------------------------------------------------
-- STEP 3. 코호트 x 경과월 별 활성 유저 수 (분자)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS cohort_active;
CREATE VIEW cohort_active AS
SELECT
    signup_month,
    month_offset,
    COUNT(DISTINCT user_id) AS active_users
FROM user_month_offset
GROUP BY signup_month, month_offset;

-- ------------------------------------------------------------
-- STEP 4. 리텐션율(%) = 분자 / 분모 * 100 (long format)
--   이 결과를 BI 툴(Tableau/Looker 등)에서 그대로 피벗하면 히트맵이 된다.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS retention_long;
CREATE VIEW retention_long AS
SELECT
    a.signup_month,
    a.month_offset,
    a.active_users,
    s.cohort_users,
    ROUND(100.0 * a.active_users / s.cohort_users, 1) AS retention_pct
FROM cohort_active a
JOIN cohort_size s ON a.signup_month = s.signup_month
ORDER BY a.signup_month, a.month_offset;

-- 확인용: long format 결과 출력
-- SELECT * FROM retention_long;

-- ------------------------------------------------------------
-- STEP 5. 코호트 x 경과월 매트릭스로 피벗 (0~9개월차)
--   SQLite는 PIVOT 문법이 없어 CASE WHEN + MAX로 직접 피벗한다.
--   analysis.py의 build_retention_matrix()와 동일한 결과여야 한다.
-- ------------------------------------------------------------
SELECT
    signup_month,
    MAX(CASE WHEN month_offset = 0 THEN retention_pct END) AS m0,
    MAX(CASE WHEN month_offset = 1 THEN retention_pct END) AS m1,
    MAX(CASE WHEN month_offset = 2 THEN retention_pct END) AS m2,
    MAX(CASE WHEN month_offset = 3 THEN retention_pct END) AS m3,
    MAX(CASE WHEN month_offset = 4 THEN retention_pct END) AS m4,
    MAX(CASE WHEN month_offset = 5 THEN retention_pct END) AS m5,
    MAX(CASE WHEN month_offset = 6 THEN retention_pct END) AS m6,
    MAX(CASE WHEN month_offset = 7 THEN retention_pct END) AS m7,
    MAX(CASE WHEN month_offset = 8 THEN retention_pct END) AS m8,
    MAX(CASE WHEN month_offset = 9 THEN retention_pct END) AS m9
FROM retention_long
GROUP BY signup_month
ORDER BY signup_month;

-- ------------------------------------------------------------
-- 참고. 채널별 리텐션 (analysis.py의 plot_channel_retention()과 대응)
-- ------------------------------------------------------------
-- SELECT
--     c.channel,
--     m.month_offset,
--     COUNT(DISTINCT m.user_id) AS active_users,
--     ROUND(100.0 * COUNT(DISTINCT m.user_id)
--           / (SELECT COUNT(DISTINCT ca.user_id)
--              FROM cohort_activity ca WHERE ca.channel = c.channel), 1) AS retention_pct
-- FROM user_month_offset m
-- JOIN (SELECT DISTINCT user_id, channel FROM cohort_activity) c ON m.user_id = c.user_id
-- GROUP BY c.channel, m.month_offset
-- ORDER BY c.channel, m.month_offset;
