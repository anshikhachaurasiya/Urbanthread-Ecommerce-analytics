"""
Runs each analysis query against PostgreSQL and exports the result set to CSV,
both for use in the Excel dashboard build script and as Power BI import files.
"""
import psycopg2
import csv
import os

DB_CONFIG = dict(host="localhost", dbname="ecommerce_analytics", user="postgres", password="postgres")
OUT_DIR = "../powerbi/exports"
os.makedirs(OUT_DIR, exist_ok=True)

QUERIES = {
    "funnel_overall": """
        WITH stage_flags AS (
            SELECT session_id,
                MAX(CASE WHEN event_type='home_view' THEN 1 ELSE 0 END) AS reached_home,
                MAX(CASE WHEN event_type='product_view' THEN 1 ELSE 0 END) AS reached_product,
                MAX(CASE WHEN event_type='add_to_cart' THEN 1 ELSE 0 END) AS reached_cart,
                MAX(CASE WHEN event_type='checkout_start' THEN 1 ELSE 0 END) AS reached_checkout,
                MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS reached_purchase
            FROM funnel_events GROUP BY session_id
        )
        SELECT 'Home View' AS stage, SUM(reached_home) AS sessions, 1 AS stage_order FROM stage_flags
        UNION ALL
        SELECT 'Product View', SUM(reached_product), 2 FROM stage_flags
        UNION ALL
        SELECT 'Add to Cart', SUM(reached_cart), 3 FROM stage_flags
        UNION ALL
        SELECT 'Checkout Start', SUM(reached_checkout), 4 FROM stage_flags
        UNION ALL
        SELECT 'Purchase', SUM(reached_purchase), 5 FROM stage_flags
        ORDER BY stage_order;
    """,
    "funnel_by_channel": """
        WITH stage_flags AS (
            SELECT s.session_id, s.channel,
                MAX(CASE WHEN fe.event_type='add_to_cart' THEN 1 ELSE 0 END) AS reached_cart,
                MAX(CASE WHEN fe.event_type='purchase' THEN 1 ELSE 0 END) AS reached_purchase
            FROM sessions s JOIN funnel_events fe ON fe.session_id=s.session_id
            GROUP BY s.session_id, s.channel
        )
        SELECT channel, COUNT(*) AS sessions, SUM(reached_purchase) AS purchases,
            ROUND(100.0*SUM(reached_purchase)/COUNT(*),2) AS conversion_rate_pct,
            ROUND(100.0*SUM(reached_cart)/COUNT(*),2) AS cart_rate_pct
        FROM stage_flags GROUP BY channel ORDER BY conversion_rate_pct DESC;
    """,
    "funnel_by_device": """
        WITH stage_flags AS (
            SELECT s.session_id, s.device,
                MAX(CASE WHEN fe.event_type='purchase' THEN 1 ELSE 0 END) AS reached_purchase
            FROM sessions s JOIN funnel_events fe ON fe.session_id=s.session_id
            GROUP BY s.session_id, s.device
        )
        SELECT device, COUNT(*) AS sessions, SUM(reached_purchase) AS purchases,
            ROUND(100.0*SUM(reached_purchase)/COUNT(*),2) AS conversion_rate_pct
        FROM stage_flags GROUP BY device ORDER BY conversion_rate_pct DESC;
    """,
    "monthly_funnel_trend": """
        WITH monthly AS (
            SELECT DATE_TRUNC('month', s.session_date)::date AS month,
                COUNT(DISTINCT s.session_id) AS sessions,
                COUNT(DISTINCT CASE WHEN fe.event_type='purchase' THEN s.session_id END) AS purchase_sessions
            FROM sessions s LEFT JOIN funnel_events fe ON fe.session_id=s.session_id
            GROUP BY 1
        )
        SELECT month, sessions, purchase_sessions,
            ROUND(100.0*purchase_sessions/NULLIF(sessions,0),2) AS conversion_rate_pct,
            ROUND(AVG(100.0*purchase_sessions/NULLIF(sessions,0))
                  OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),2) AS conv_rate_3mo_avg
        FROM monthly ORDER BY month;
    """,
    "cohort_retention": """
        WITH cohort AS (
            SELECT customer_id, DATE_TRUNC('month', signup_date)::date AS cohort_month FROM customers
        ),
        order_months AS (
            SELECT DISTINCT o.customer_id, DATE_TRUNC('month', o.order_date)::date AS order_month
            FROM orders o WHERE o.order_status <> 'Cancelled'
        ),
        cohort_activity AS (
            SELECT c.cohort_month, c.customer_id, om.order_month,
                (DATE_PART('year', om.order_month) - DATE_PART('year', c.cohort_month)) * 12
                  + (DATE_PART('month', om.order_month) - DATE_PART('month', c.cohort_month)) AS month_index
            FROM cohort c JOIN order_months om ON om.customer_id = c.customer_id
        ),
        cohort_size AS (
            SELECT cohort_month, COUNT(*) AS cohort_customers FROM cohort GROUP BY cohort_month
        )
        SELECT ca.cohort_month, cs.cohort_customers, ca.month_index,
            COUNT(DISTINCT ca.customer_id) AS active_customers,
            ROUND(100.0*COUNT(DISTINCT ca.customer_id)/cs.cohort_customers,2) AS retention_pct
        FROM cohort_activity ca JOIN cohort_size cs ON cs.cohort_month = ca.cohort_month
        WHERE ca.month_index BETWEEN 0 AND 6
        GROUP BY ca.cohort_month, cs.cohort_customers, ca.month_index
        ORDER BY ca.cohort_month, ca.month_index;
    """,
    "rfm_segments": """
        WITH order_agg AS (
            SELECT customer_id, MAX(order_date) AS last_order_date, COUNT(*) AS frequency, SUM(total_amount) AS monetary
            FROM orders WHERE order_status='Delivered' GROUP BY customer_id
        ),
        scored AS (
            SELECT customer_id, frequency, monetary,
                (SELECT MAX(order_date) FROM orders) - last_order_date AS recency_days,
                NTILE(4) OVER (ORDER BY (SELECT MAX(order_date) FROM orders) - last_order_date DESC) AS r_score,
                NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
                NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
            FROM order_agg
        ),
        segmented AS (
            SELECT *,
                CASE
                    WHEN r_score>=3 AND f_score>=3 AND m_score>=3 THEN 'Champions'
                    WHEN r_score>=3 AND f_score>=2 THEN 'Loyal Customers'
                    WHEN r_score<=2 AND f_score>=3 THEN 'At Risk'
                    WHEN r_score<=2 AND f_score<=2 AND m_score<=2 THEN 'Lost / Dormant'
                    ELSE 'Needs Attention'
                END AS rfm_segment
            FROM scored
        )
        SELECT rfm_segment, COUNT(*) AS customers,
            ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),2) AS pct_of_customers,
            ROUND(AVG(monetary),2) AS avg_monetary, ROUND(SUM(monetary),2) AS total_revenue
        FROM segmented GROUP BY rfm_segment ORDER BY total_revenue DESC;
    """,
    "ab_test_results": """
        WITH session_outcomes AS (
            SELECT aba.session_id, aba.variant,
                MAX(CASE WHEN fe.event_type='purchase' THEN 1 ELSE 0 END) AS purchased
            FROM ab_test_assignments aba JOIN funnel_events fe ON fe.session_id=aba.session_id
            WHERE aba.test_name='checkout_redesign_v2' GROUP BY aba.session_id, aba.variant
        )
        SELECT variant, COUNT(*) AS sessions_in_checkout, SUM(purchased) AS purchases,
            ROUND(100.0*SUM(purchased)/COUNT(*),2) AS completion_rate_pct
        FROM session_outcomes GROUP BY variant ORDER BY variant;
    """,
    "marketing_channel_roi": """
        WITH channel_orders AS (
            SELECT s.channel, DATE_TRUNC('month', o.order_date)::date AS month,
                COUNT(DISTINCT o.order_id) AS orders, SUM(o.total_amount) AS revenue
            FROM orders o JOIN sessions s ON s.session_id=o.session_id
            WHERE o.order_status<>'Cancelled' GROUP BY s.channel, DATE_TRUNC('month', o.order_date)
        )
        SELECT ms.channel, SUM(ms.spend_inr) AS total_spend,
            COALESCE(SUM(co.orders),0) AS attributed_orders,
            COALESCE(SUM(co.revenue),0) AS attributed_revenue,
            ROUND(SUM(ms.spend_inr)/NULLIF(SUM(co.orders),0),2) AS cac_inr,
            ROUND(COALESCE(SUM(co.revenue),0)/NULLIF(SUM(ms.spend_inr),0),2) AS roas
        FROM marketing_spend ms LEFT JOIN channel_orders co ON co.channel=ms.channel AND co.month=ms.month
        GROUP BY ms.channel ORDER BY roas DESC NULLS LAST;
    """,
    "category_performance": """
        SELECT p.category, COUNT(DISTINCT oi.order_id) AS orders, SUM(oi.quantity) AS units_sold,
            SUM(oi.quantity*oi.unit_price) AS gross_revenue,
            SUM(oi.quantity*(oi.unit_price-p.unit_cost)) AS gross_margin,
            ROUND(100.0*SUM(oi.quantity*(oi.unit_price-p.unit_cost))/NULLIF(SUM(oi.quantity*oi.unit_price),0),2) AS margin_pct,
            ROUND(100.0*SUM(CASE WHEN o.order_status='Returned' THEN 1 ELSE 0 END)/COUNT(DISTINCT oi.order_id),2) AS return_rate_pct
        FROM order_items oi JOIN products p ON p.product_id=oi.product_id JOIN orders o ON o.order_id=oi.order_id
        GROUP BY p.category ORDER BY gross_revenue DESC;
    """,
}


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    for name, sql in QUERIES.items():
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
        path = f"{OUT_DIR}/{name}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)
        print(f"exported {len(rows):>4} rows -> {path}")
    conn.close()


if __name__ == "__main__":
    main()
