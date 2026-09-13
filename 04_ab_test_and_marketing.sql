-- ============================================================================
-- 04_ab_test_and_marketing.sql
-- Purpose: (a) Evaluate the checkout redesign A/B test (checkout_start -> purchase)
--          (b) Marketing channel spend efficiency (CAC, ROAS)
-- ============================================================================

-- 4.1 A/B test: checkout completion rate, Variant A (control) vs B (redesign)
WITH session_outcomes AS (
    SELECT
        aba.session_id,
        aba.variant,
        MAX(CASE WHEN fe.event_type = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM ab_test_assignments aba
    JOIN funnel_events fe ON fe.session_id = aba.session_id
    WHERE aba.test_name = 'checkout_redesign_v2'
    GROUP BY aba.session_id, aba.variant
)
SELECT
    variant,
    COUNT(*) AS sessions_in_checkout,
    SUM(purchased) AS purchases,
    ROUND(100.0 * SUM(purchased) / COUNT(*), 2) AS completion_rate_pct
FROM session_outcomes
GROUP BY variant
ORDER BY variant;

-- 4.2 Two-proportion z-test inputs (compute z-score / lift directly in SQL;
--     significance interpreted in Python, see notebooks/ab_test_stats.py)
WITH session_outcomes AS (
    SELECT
        aba.variant,
        COUNT(*) AS n,
        SUM(CASE WHEN fe.event_type = 'purchase' THEN 1 ELSE 0 END) AS conversions
    FROM ab_test_assignments aba
    JOIN funnel_events fe ON fe.session_id = aba.session_id
    WHERE aba.test_name = 'checkout_redesign_v2'
    GROUP BY aba.variant, aba.session_id
),
agg AS (
    SELECT variant, COUNT(*) AS n, SUM(conversions) AS conversions
    FROM session_outcomes
    GROUP BY variant
)
SELECT * FROM agg ORDER BY variant;

-- 4.3 Marketing channel efficiency: spend, clicks, resulting orders & revenue,
--     CAC (cost per acquisition) and ROAS (return on ad spend)
WITH channel_orders AS (
    SELECT
        s.channel,
        DATE_TRUNC('month', o.order_date)::date AS month,
        COUNT(DISTINCT o.order_id) AS orders,
        SUM(o.total_amount) AS revenue
    FROM orders o
    JOIN sessions s ON s.session_id = o.session_id
    WHERE o.order_status <> 'Cancelled'
    GROUP BY s.channel, DATE_TRUNC('month', o.order_date)
)
SELECT
    ms.channel,
    SUM(ms.spend_inr) AS total_spend,
    COALESCE(SUM(co.orders), 0) AS attributed_orders,
    COALESCE(SUM(co.revenue), 0) AS attributed_revenue,
    ROUND(SUM(ms.spend_inr) / NULLIF(SUM(co.orders), 0), 2) AS cac_inr,
    ROUND(COALESCE(SUM(co.revenue), 0) / NULLIF(SUM(ms.spend_inr), 0), 2) AS roas
FROM marketing_spend ms
LEFT JOIN channel_orders co ON co.channel = ms.channel AND co.month = ms.month
GROUP BY ms.channel
ORDER BY roas DESC NULLS LAST;

-- 4.4 Category-level performance: revenue, margin, return rate
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id) AS orders,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.quantity * oi.unit_price) AS gross_revenue,
    SUM(oi.quantity * (oi.unit_price - p.unit_cost)) AS gross_margin,
    ROUND(100.0 * SUM(oi.quantity * (oi.unit_price - p.unit_cost))
          / NULLIF(SUM(oi.quantity * oi.unit_price), 0), 2) AS margin_pct,
    ROUND(100.0 * SUM(CASE WHEN o.order_status = 'Returned' THEN 1 ELSE 0 END)
          / COUNT(DISTINCT oi.order_id), 2) AS return_rate_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
GROUP BY p.category
ORDER BY gross_revenue DESC;
