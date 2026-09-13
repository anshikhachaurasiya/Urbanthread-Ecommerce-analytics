-- ============================================================================
-- 02_funnel_analysis.sql
-- Purpose: Measure conversion through the browse -> purchase funnel, overall
--          and cut by acquisition channel and device.
-- ============================================================================

-- 2.1 Overall funnel: sessions reaching each stage, and stage-to-stage conversion
WITH stage_flags AS (
    SELECT
        session_id,
        MAX(CASE WHEN event_type = 'home_view'      THEN 1 ELSE 0 END) AS reached_home,
        MAX(CASE WHEN event_type = 'product_view'    THEN 1 ELSE 0 END) AS reached_product,
        MAX(CASE WHEN event_type = 'add_to_cart'     THEN 1 ELSE 0 END) AS reached_cart,
        MAX(CASE WHEN event_type = 'checkout_start'  THEN 1 ELSE 0 END) AS reached_checkout,
        MAX(CASE WHEN event_type = 'purchase'        THEN 1 ELSE 0 END) AS reached_purchase
    FROM funnel_events
    GROUP BY session_id
)
SELECT
    SUM(reached_home)      AS home_view_sessions,
    SUM(reached_product)   AS product_view_sessions,
    SUM(reached_cart)      AS add_to_cart_sessions,
    SUM(reached_checkout)  AS checkout_start_sessions,
    SUM(reached_purchase)  AS purchase_sessions,
    ROUND(100.0 * SUM(reached_product)  / NULLIF(SUM(reached_home),0), 2)    AS pct_home_to_product,
    ROUND(100.0 * SUM(reached_cart)     / NULLIF(SUM(reached_product),0), 2) AS pct_product_to_cart,
    ROUND(100.0 * SUM(reached_checkout) / NULLIF(SUM(reached_cart),0), 2)    AS pct_cart_to_checkout,
    ROUND(100.0 * SUM(reached_purchase) / NULLIF(SUM(reached_checkout),0),2) AS pct_checkout_to_purchase,
    ROUND(100.0 * SUM(reached_purchase) / NULLIF(SUM(reached_home),0), 2)    AS pct_overall_conversion
FROM stage_flags;

-- 2.2 Funnel conversion by acquisition channel (session-level channel)
WITH stage_flags AS (
    SELECT
        s.session_id,
        s.channel,
        MAX(CASE WHEN fe.event_type = 'home_view'     THEN 1 ELSE 0 END) AS reached_home,
        MAX(CASE WHEN fe.event_type = 'add_to_cart'   THEN 1 ELSE 0 END) AS reached_cart,
        MAX(CASE WHEN fe.event_type = 'purchase'      THEN 1 ELSE 0 END) AS reached_purchase
    FROM sessions s
    JOIN funnel_events fe ON fe.session_id = s.session_id
    GROUP BY s.session_id, s.channel
)
SELECT
    channel,
    COUNT(*)                                   AS sessions,
    SUM(reached_purchase)                      AS purchases,
    ROUND(100.0 * SUM(reached_purchase) / COUNT(*), 2)  AS conversion_rate_pct,
    ROUND(100.0 * SUM(reached_cart) / COUNT(*), 2)      AS cart_rate_pct
FROM stage_flags
GROUP BY channel
ORDER BY conversion_rate_pct DESC;

-- 2.3 Funnel conversion by device type
WITH stage_flags AS (
    SELECT
        s.session_id,
        s.device,
        MAX(CASE WHEN fe.event_type = 'purchase' THEN 1 ELSE 0 END) AS reached_purchase
    FROM sessions s
    JOIN funnel_events fe ON fe.session_id = s.session_id
    GROUP BY s.session_id, s.device
)
SELECT
    device,
    COUNT(*) AS sessions,
    SUM(reached_purchase) AS purchases,
    ROUND(100.0 * SUM(reached_purchase) / COUNT(*), 2) AS conversion_rate_pct
FROM stage_flags
GROUP BY device
ORDER BY conversion_rate_pct DESC;

-- 2.4 Monthly funnel trend (top-of-funnel sessions vs purchases, with 3-month moving avg)
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', s.session_date)::date AS month,
        COUNT(DISTINCT s.session_id) AS sessions,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN s.session_id END) AS purchase_sessions
    FROM sessions s
    LEFT JOIN funnel_events fe ON fe.session_id = s.session_id
    GROUP BY 1
)
SELECT
    month,
    sessions,
    purchase_sessions,
    ROUND(100.0 * purchase_sessions / NULLIF(sessions,0), 2) AS conversion_rate_pct,
    ROUND(AVG(100.0 * purchase_sessions / NULLIF(sessions,0))
          OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS conv_rate_3mo_avg
FROM monthly
ORDER BY month;
