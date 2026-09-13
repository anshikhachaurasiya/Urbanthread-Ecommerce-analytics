# Power BI Dashboard — Build Guide

Power BI Desktop is Windows-only, so the `.pbix` itself has to be built on your
own machine — this folder gives you everything ready to drop in so that part
takes ~30–45 minutes instead of starting from a blank canvas.

## 1. Get data

Two options, use either:

**Option A — connect Power BI directly to Postgres (recommended, shows a real live connection in your project):**
`Get Data → PostgreSQL database → Server: localhost, Database: ecommerce_analytics`
(requires the Npgsql driver — Power BI will prompt you to install it if missing)
Import these tables: `customers`, `products`, `orders`, `order_items`, `sessions`, `marketing_spend`.

**Option B — import the flat CSVs in `raw_tables/`** (no Postgres connection needed):
`Get Data → Text/CSV` → import each file in `raw_tables/`.

Either way, also import the pre-aggregated CSVs in `exports/` as separate tables —
these back the funnel, cohort, RFM, and A/B test visuals directly (no DAX needed
for those, since retention-matrix and z-test logic is easier in SQL than DAX).

## 2. Build relationships (Model view)

```
customers (customer_id) 1───* orders (customer_id)
orders (order_id)        1───* order_items (order_id)
products (product_id)    1───* order_items (product_id)
customers (customer_id)  1───* sessions (customer_id)
```
Mark `orders[order_date]` as a Date table (or add a separate calendar table via
`New Table → CalendarDate = CALENDAR(MIN(orders[order_date]), MAX(orders[order_date]))`)
if you want native Power BI time-intelligence functions on top of the monthly
trend already computed in SQL.

## 3. DAX measures to add

Paste these into a new measures table (`New Table` → name it `_Measures`, or add
directly on the `orders` table):

```DAX
Total Revenue = SUM(orders[total_amount])

Total Orders = DISTINCTCOUNT(orders[order_id])

AOV = DIVIDE([Total Revenue], [Total Orders])

Delivered Orders = CALCULATE([Total Orders], orders[order_status] = "Delivered")

Return Rate % = DIVIDE(
    CALCULATE([Total Orders], orders[order_status] = "Returned"),
    [Total Orders]
)

Gross Margin = SUMX(
    order_items,
    order_items[quantity] * (order_items[unit_price] - RELATED(products[unit_cost]))
)

Margin % = DIVIDE([Gross Margin], SUMX(order_items, order_items[quantity]*order_items[unit_price]))

Active Customers = DISTINCTCOUNT(orders[customer_id])

Revenue MoM % = 
VAR CurrMonth = [Total Revenue]
VAR PrevMonth = CALCULATE([Total Revenue], DATEADD('CalendarDate'[Date], -1, MONTH))
RETURN DIVIDE(CurrMonth - PrevMonth, PrevMonth)
```

For the funnel, cohort retention matrix, RFM segments, and A/B test result —
import the corresponding CSV from `exports/` as its own table and build the
visual straight off those pre-aggregated columns (a Funnel visual on
`funnel_overall`, a Matrix visual on `cohort_retention` with `cohort_month` on
rows and `month_index` on columns, values = `retention_pct`, and conditional
formatting for the heatmap look).

## 4. Suggested pages

1. **Executive Overview** — KPI cards (Total Revenue, Overall Conversion %,
   AOV, Active Customers), a revenue trend line, category donut.
2. **Funnel & Channel** — Funnel visual (`exports/funnel_overall.csv`), bar
   chart of conversion rate by channel/device.
3. **Retention & RFM** — Matrix heatmap (`cohort_retention.csv`), RFM segment
   donut + table (`rfm_segments.csv`).
4. **A/B Test** — Two KPI cards (Variant A vs B completion rate),
   `ab_test_results.csv`, plus a text box with the z-test / p-value writeup
   from `scripts/ab_test_stats.py`.
5. **Marketing ROI** — Bar chart of CAC and ROAS by channel
   (`marketing_channel_roi.csv`).

## 5. Once built

Export a couple of PNG screenshots of the finished pages and drop them into
`docs/screenshots/` before pushing to GitHub — a README with only text and no
visual is a much weaker portfolio piece. Also File → Publish to Power BI
service if you want a shareable live link to put in your resume/LinkedIn.
