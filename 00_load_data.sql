-- ============================================================================
-- 00_load_data.sql
-- Bulk-loads the CSVs in /data into the tables created by 01_schema.sql.
-- Run 01_schema.sql first. Adjust the path below to wherever you cloned the repo.
-- ============================================================================

\copy customers            FROM 'data/customers.csv'            WITH (FORMAT csv, HEADER true);
\copy products              FROM 'data/products.csv'              WITH (FORMAT csv, HEADER true);
\copy sessions               FROM 'data/sessions.csv'               WITH (FORMAT csv, HEADER true);
\copy funnel_events           FROM 'data/funnel_events.csv'           WITH (FORMAT csv, HEADER true);
\copy orders                   FROM 'data/orders.csv'                   WITH (FORMAT csv, HEADER true);
\copy order_items               FROM 'data/order_items.csv'               WITH (FORMAT csv, HEADER true);
\copy marketing_spend             FROM 'data/marketing_spend.csv'             WITH (FORMAT csv, HEADER true);
\copy ab_test_assignments           FROM 'data/ab_test_assignments.csv'           WITH (FORMAT csv, HEADER true);
