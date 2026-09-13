"""
Two-proportion z-test for the checkout redesign A/B test (checkout_redesign_v2).
Pulls variant-level session/conversion counts from PostgreSQL and tests whether
Variant B (redesigned checkout) converts significantly better than Variant A (control).

Run: python3 ab_test_stats.py
Requires: psycopg2-binary, scipy, statsmodels (or a manual z-test if unavailable)
"""

import math
import psycopg2

DB_CONFIG = dict(host="localhost", dbname="ecommerce_analytics", user="postgres", password="postgres")

QUERY = """
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
SELECT variant, COUNT(*) AS n, SUM(purchased) AS conversions
FROM session_outcomes
GROUP BY variant
ORDER BY variant;
"""


def two_proportion_z_test(x1, n1, x2, n2):
    """Manual two-proportion z-test (no scipy dependency required)."""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se
    # two-tailed p-value via error function approximation
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return p1, p2, z, p_value


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(QUERY)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = {variant: (n, conversions) for variant, n, conversions in rows}
    n_a, x_a = data["A"]
    n_b, x_b = data["B"]

    p1, p2, z, p_value = two_proportion_z_test(x_a, n_a, x_b, n_b)
    lift = (p2 - p1) / p1 * 100

    print("=== Checkout Redesign A/B Test: checkout_redesign_v2 ===")
    print(f"Variant A (control):   n={n_a:,}  conversions={x_a:,}  rate={p1*100:.2f}%")
    print(f"Variant B (redesign):  n={n_b:,}  conversions={x_b:,}  rate={p2*100:.2f}%")
    print(f"Relative lift:         {lift:+.1f}%")
    print(f"z-statistic:           {z:.3f}")
    print(f"p-value (two-tailed):  {p_value:.4f}")
    print(f"Significant at 5%?     {'YES' if p_value < 0.05 else 'No'}")


if __name__ == "__main__":
    main()
