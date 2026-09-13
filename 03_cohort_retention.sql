-- ============================================================================
-- 03_cohort_retention.sql
-- Purpose: Monthly signup-cohort retention matrix based on repeat order
--          activity, using window functions and CTEs.
-- ============================================================================

-- 3.1 Cohort retention matrix: % of each signup-month cohort placing an order
--     in month 0, 1, 2, ... after signup
WITH cohort AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers
),
order_months AS (
    SELECT DISTINCT
        o.customer_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month
    FROM orders o
    WHERE o.order_status <> 'Cancelled'
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        c.customer_id,
        om.order_month,
        (DATE_PART('year', om.order_month) - DATE_PART('year', c.cohort_month)) * 12
          + (DATE_PART('month', om.order_month) - DATE_PART('month', c.cohort_month)) AS month_index
    FROM cohort c
    JOIN order_months om ON om.customer_id = c.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM cohort
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_customers,
    ca.month_index,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_customers, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs ON cs.cohort_month = ca.cohort_month
WHERE ca.month_index BETWEEN 0 AND 6
GROUP BY ca.cohort_month, cs.cohort_customers, ca.month_index
ORDER BY ca.cohort_month, ca.month_index;

-- 3.2 Simple customer-level RFM segmentation (Recency, Frequency, Monetary)
WITH order_agg AS (
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date,
        COUNT(*) AS frequency,
        SUM(total_amount) AS monetary
    FROM orders
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
scored AS (
    SELECT
        customer_id,
        last_order_date,
        frequency,
        monetary,
        (SELECT MAX(order_date) FROM orders) - last_order_date AS recency_days,
        NTILE(4) OVER (ORDER BY (SELECT MAX(order_date) FROM orders) - last_order_date DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM order_agg
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal Customers'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost / Dormant'
        ELSE 'Needs Attention'
    END AS rfm_segment
FROM scored
ORDER BY monetary DESC;

-- 3.3 Segment summary (for the dashboard)
WITH order_agg AS (
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date,
        COUNT(*) AS frequency,
        SUM(total_amount) AS monetary
    FROM orders
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
scored AS (
    SELECT
        customer_id, frequency, monetary,
        (SELECT MAX(order_date) FROM orders) - last_order_date AS recency_days,
        NTILE(4) OVER (ORDER BY (SELECT MAX(order_date) FROM orders) - last_order_date DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM order_agg
),
segmented AS (
    SELECT *,
        CASE
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal Customers'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost / Dormant'
            ELSE 'Needs Attention'
        END AS rfm_segment
    FROM scored
)
SELECT
    rfm_segment,
    COUNT(*) AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_customers,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(SUM(monetary), 2) AS total_revenue
FROM segmented
GROUP BY rfm_segment
ORDER BY total_revenue DESC;
