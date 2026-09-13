# Entity-Relationship Diagram

```mermaid
erDiagram
    customers ||--o{ sessions : has
    customers ||--o{ orders : places
    sessions ||--o{ funnel_events : generates
    sessions ||--o| orders : converts_to
    orders ||--o{ order_items : contains
    products ||--o{ order_items : sold_in
    sessions ||--o{ ab_test_assignments : assigned

    customers {
        int customer_id PK
        date signup_date
        varchar city
        varchar acquisition_channel
        varchar gender
        varchar age_group
    }
    products {
        int product_id PK
        varchar category
        varchar sub_category
        varchar brand
        numeric list_price
        numeric unit_cost
    }
    sessions {
        int session_id PK
        int customer_id FK
        date session_date
        varchar device
        varchar channel
    }
    funnel_events {
        int event_id PK
        int session_id FK
        int customer_id FK
        varchar event_type
        timestamp event_timestamp
    }
    orders {
        int order_id PK
        int customer_id FK
        int session_id FK
        date order_date
        varchar order_status
        varchar payment_method
        numeric total_amount
    }
    order_items {
        int order_item_id PK
        int order_id FK
        int product_id FK
        int quantity
        numeric unit_price
    }
    marketing_spend {
        date month PK
        varchar channel PK
        numeric spend_inr
        bigint impressions
        bigint clicks
    }
    ab_test_assignments {
        int customer_id FK
        int session_id FK
        varchar test_name
        char variant
    }
```

`funnel_events.event_type` is a state machine: `home_view → product_view →
add_to_cart → checkout_start → purchase`. A session can stop at any stage;
only sessions that reach `purchase` have a matching row in `orders`.
