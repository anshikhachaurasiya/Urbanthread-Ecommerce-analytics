-- ============================================================================
-- UrbanThread E-commerce Funnel & Retention Analytics
-- Schema: 01_schema.sql
-- Author: Anshikha Chaurasiya
-- Description: Star-ish schema for a fashion e-commerce platform capturing
--              customers, product catalog, browsing sessions, funnel events,
--              orders, and marketing spend. Built in PostgreSQL 16.
-- ============================================================================

DROP TABLE IF EXISTS ab_test_assignments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS funnel_events CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS marketing_spend CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    signup_date          DATE NOT NULL,
    city                 VARCHAR(50),
    acquisition_channel  VARCHAR(30),
    gender               VARCHAR(10),
    age_group            VARCHAR(10)
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    category      VARCHAR(40) NOT NULL,
    sub_category  VARCHAR(40),
    brand         VARCHAR(40),
    list_price    NUMERIC(10,2) NOT NULL CHECK (list_price >= 0),
    unit_cost     NUMERIC(10,2) NOT NULL CHECK (unit_cost >= 0)
);

CREATE TABLE sessions (
    session_id    INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    session_date  DATE NOT NULL,
    device        VARCHAR(10),
    channel       VARCHAR(30)
);

CREATE TABLE funnel_events (
    event_id        INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id),
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    event_type      VARCHAR(20) NOT NULL CHECK (
                        event_type IN ('home_view','product_view','add_to_cart',
                                       'checkout_start','purchase')),
    event_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    session_id      INTEGER REFERENCES sessions(session_id),
    order_date      DATE NOT NULL,
    order_status    VARCHAR(15) NOT NULL CHECK (
                        order_status IN ('Delivered','Returned','Cancelled')),
    payment_method  VARCHAR(20),
    discount_pct    NUMERIC(5,2) DEFAULT 0,
    total_amount    NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0)
);

CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(10,2) NOT NULL
);

CREATE TABLE marketing_spend (
    month        DATE NOT NULL,
    channel      VARCHAR(30) NOT NULL,
    spend_inr    NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions  BIGINT,
    clicks       BIGINT,
    PRIMARY KEY (month, channel)
);

CREATE TABLE ab_test_assignments (
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    session_id   INTEGER NOT NULL REFERENCES sessions(session_id),
    test_name    VARCHAR(40) NOT NULL,
    variant      CHAR(1) NOT NULL CHECK (variant IN ('A','B')),
    PRIMARY KEY (session_id, test_name)
);

-- ---------------------------------------------------------------------------
-- Indexes to support the analysis queries in 02_analysis_queries.sql
-- ---------------------------------------------------------------------------
CREATE INDEX idx_sessions_customer      ON sessions(customer_id);
CREATE INDEX idx_sessions_date          ON sessions(session_date);
CREATE INDEX idx_funnel_session         ON funnel_events(session_id);
CREATE INDEX idx_funnel_customer        ON funnel_events(customer_id);
CREATE INDEX idx_funnel_event_type      ON funnel_events(event_type);
CREATE INDEX idx_orders_customer        ON orders(customer_id);
CREATE INDEX idx_orders_date            ON orders(order_date);
CREATE INDEX idx_order_items_order      ON order_items(order_id);
CREATE INDEX idx_order_items_product    ON order_items(product_id);
