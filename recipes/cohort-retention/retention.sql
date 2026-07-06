-- ============================================================
-- SaaS monthly cohort retention analysis (SQL version)
-- Data: data/cohort_activity.csv (loaded into SQLite as the cohort_activity table)
--   Columns: user_id, signup_month (YYYY-MM), plan, channel, activity_month (YYYY-MM)
--   One row = "this user was active in this month." The signup-month row is
--   included too.
--
-- Run (SQLite CLI):
--   sqlite3 cohort.db
--   .mode csv
--   .import data/cohort_activity.csv cohort_activity
--   .read retention.sql
-- ============================================================

-- ------------------------------------------------------------
-- STEP 0. Expression for converting a month string (YYYY-MM) into an integer month index
--   month_index = year*12 + month  ->  the difference between two months is
--   the elapsed month count (month_offset)
--   SQLite has no DATE_DIFF, so we compute it by slicing the strings.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- STEP 1. Total users per cohort (denominator)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS cohort_size;
CREATE VIEW cohort_size AS
SELECT
    signup_month,
    COUNT(DISTINCT user_id) AS cohort_users
FROM cohort_activity
GROUP BY signup_month;

-- ------------------------------------------------------------
-- STEP 2. User x activity month -> months elapsed since signup (month_offset)
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
-- STEP 3. Active users per cohort x month offset (numerator)
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
-- STEP 4. Retention rate (%) = numerator / denominator * 100 (long format)
--   Pivoting this result directly in a BI tool (Tableau/Looker, etc.) yields the heatmap.
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

-- For inspection: print the long-format result
-- SELECT * FROM retention_long;

-- ------------------------------------------------------------
-- STEP 5. Pivot into a cohort x month-offset matrix (months 0-9)
--   SQLite has no PIVOT syntax, so we pivot manually with CASE WHEN + MAX.
--   This should match analysis.py's build_retention_matrix() exactly.
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
-- Reference. Retention by channel (mirrors analysis.py's plot_channel_retention())
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
