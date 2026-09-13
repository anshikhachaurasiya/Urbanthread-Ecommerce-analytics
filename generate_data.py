"""
Synthetic data generator for the Fashion E-commerce Funnel & Retention Analytics project.
Generates realistic-looking (but fully synthetic) data for a fictional fashion e-commerce
platform called 'UrbanThread', across 14 months (Nov 2024 - Dec 2025).

Run: python3 generate_data.py
Outputs CSVs into ../data/
"""

import random
import csv
import datetime as dt
from collections import defaultdict

random.seed(42)

OUT_DIR = "../data"

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai",
          "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Gorakhpur", "Indore",
          "Chandigarh", "Kochi", "Bhopal"]

CHANNELS = ["Organic Search", "Paid Social", "Paid Search", "Direct",
            "Affiliate", "Email", "Referral"]

CHANNEL_WEIGHTS = [0.22, 0.20, 0.18, 0.15, 0.10, 0.08, 0.07]

DEVICES = ["Mobile", "Desktop", "Tablet"]
DEVICE_WEIGHTS = [0.68, 0.27, 0.05]

CATEGORIES = {
    "Men's Apparel": ["T-Shirts", "Shirts", "Jeans", "Ethnic Wear", "Jackets"],
    "Women's Apparel": ["Kurtis", "Dresses", "Tops", "Sarees", "Leggings"],
    "Footwear": ["Sneakers", "Sandals", "Formal Shoes", "Sports Shoes"],
    "Accessories": ["Bags", "Watches", "Belts", "Sunglasses"],
    "Beauty": ["Skincare", "Haircare", "Makeup"],
}

BRANDS_BY_CAT = {
    "Men's Apparel": ["Urban Threads", "Denimo", "Aravalli", "FitLine"],
    "Women's Apparel": ["Chiffon Co", "Meraki", "Zariya", "Aravalli"],
    "Footwear": ["Strydo", "ComfortWalk", "SprintX"],
    "Accessories": ["Carryall", "TimeKeep", "Solstice"],
    "Beauty": ["Glowly", "PureSkin", "NatureLux"],
}

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54"]
GENDERS = ["Female", "Male", "Other"]

START_DATE = dt.date(2024, 11, 1)
END_DATE = dt.date(2025, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

N_CUSTOMERS = 9000
N_PRODUCTS = 260

FUNNEL_STAGES = ["home_view", "product_view", "add_to_cart", "checkout_start", "purchase"]
# Base conversion probabilities stage-to-stage (will be modulated by channel/device)
BASE_STEP_CONV = {
    "home_view->product_view": 0.62,
    "product_view->add_to_cart": 0.34,
    "add_to_cart->checkout_start": 0.52,
    "checkout_start->purchase": 0.68,
}

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "COD"]
PAYMENT_WEIGHTS = [0.38, 0.20, 0.16, 0.10, 0.16]


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def random_date(start, end):
    delta = (end - start).days
    return start + dt.timedelta(days=random.randint(0, delta))


def gen_products():
    products = []
    pid = 1
    for _ in range(N_PRODUCTS):
        cat = random.choice(list(CATEGORIES.keys()))
        sub = random.choice(CATEGORIES[cat])
        brand = random.choice(BRANDS_BY_CAT[cat])
        base_price = {
            "Men's Apparel": random.randint(499, 2999),
            "Women's Apparel": random.randint(599, 3499),
            "Footwear": random.randint(999, 4999),
            "Accessories": random.randint(299, 2499),
            "Beauty": random.randint(199, 1499),
        }[cat]
        cost = round(base_price * random.uniform(0.42, 0.58))
        products.append({
            "product_id": pid,
            "category": cat,
            "sub_category": sub,
            "brand": brand,
            "list_price": base_price,
            "unit_cost": cost,
        })
        pid += 1
    return products


def gen_customers():
    customers = []
    # Spread signups across the window, with growth over time (more recent months = more signups)
    for cid in range(1, N_CUSTOMERS + 1):
        # weight signup date towards later months to mimic a growing platform
        t = random.random() ** 1.6  # skew towards 1 (later dates)
        signup_offset = int(t * TOTAL_DAYS)
        signup_date = START_DATE + dt.timedelta(days=signup_offset)
        channel = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)
        customers.append({
            "customer_id": cid,
            "signup_date": signup_date,
            "city": random.choice(CITIES),
            "acquisition_channel": channel,
            "gender": weighted_choice(GENDERS, [0.54, 0.44, 0.02]),
            "age_group": random.choice(AGE_GROUPS),
        })
    return customers


def channel_quality_multiplier(channel):
    # Some channels bring higher-intent traffic than others
    return {
        "Organic Search": 1.05,
        "Paid Social": 0.85,
        "Paid Search": 1.00,
        "Direct": 1.20,
        "Affiliate": 0.80,
        "Email": 1.15,
        "Referral": 1.10,
    }[channel]


def device_quality_multiplier(device):
    return {"Mobile": 0.92, "Desktop": 1.18, "Tablet": 1.00}[device]


def main():
    products = gen_products()
    customers = gen_customers()
    cust_by_id = {c["customer_id"]: c for c in customers}

    sessions = []
    funnel_events = []
    orders = []
    order_items = []
    ab_assignments = []

    session_id = 1
    event_id = 1
    order_id = 1
    order_item_id = 1

    # A/B test: new checkout page, ran for 6 weeks (2025-07-01 to 2025-08-11)
    ab_start = dt.date(2025, 7, 1)
    ab_end = dt.date(2025, 8, 11)

    for cust in customers:
        # number of sessions this customer has, correlated with recency and random engagement level
        days_active = (END_DATE - cust["signup_date"]).days
        if days_active <= 0:
            continue
        engagement = random.random()  # 0=low engagement, 1=high engagement
        expected_sessions = max(1, int((1 + engagement * 6) * (days_active / TOTAL_DAYS) * 4))
        n_sessions = max(1, min(expected_sessions, 40))

        # Determine simple retention decay: probability customer churns after N days of inactivity
        last_session_date = cust["signup_date"]

        for s in range(n_sessions):
            # sessions cluster somewhat after signup, with periodic return visits
            gap = int(random.expovariate(1 / max(6, 40 * (1 - engagement))))
            candidate_date = last_session_date + dt.timedelta(days=max(1, gap))
            if candidate_date > END_DATE:
                break
            last_session_date = candidate_date

            device = weighted_choice(DEVICES, DEVICE_WEIGHTS)
            channel = cust["acquisition_channel"] if random.random() < 0.55 else weighted_choice(CHANNELS, CHANNEL_WEIGHTS)

            sessions.append({
                "session_id": session_id,
                "customer_id": cust["customer_id"],
                "session_date": candidate_date,
                "device": device,
                "channel": channel,
            })

            # ---- funnel walk for this session ----
            quality = channel_quality_multiplier(channel) * device_quality_multiplier(device)
            stage_reached = 0  # index into FUNNEL_STAGES
            ts_base = dt.datetime.combine(candidate_date, dt.time(random.randint(7, 23), random.randint(0, 59)))
            cur_ts = ts_base

            funnel_events.append({
                "event_id": event_id, "session_id": session_id, "customer_id": cust["customer_id"],
                "event_type": FUNNEL_STAGES[0], "event_timestamp": cur_ts,
            })
            event_id += 1
            stage_reached = 0

            # AB test assignment applies to checkout-related conversion for eligible sessions
            in_ab_window = ab_start <= candidate_date <= ab_end
            variant = None
            if in_ab_window:
                # sticky assignment per customer for the test
                variant = "B" if (cust["customer_id"] % 2 == 0) else "A"

            keys = ["home_view->product_view", "product_view->add_to_cart",
                    "add_to_cart->checkout_start", "checkout_start->purchase"]
            for i, key in enumerate(keys):
                p = BASE_STEP_CONV[key] * min(1.4, quality)
                if key == "checkout_start->purchase" and in_ab_window:
                    # Variant B = redesigned checkout, lifts purchase completion
                    p = p * (1.30 if variant == "B" else 1.0)
                p = min(0.95, p)
                if random.random() < p:
                    cur_ts += dt.timedelta(minutes=random.randint(1, 25))
                    funnel_events.append({
                        "event_id": event_id, "session_id": session_id, "customer_id": cust["customer_id"],
                        "event_type": FUNNEL_STAGES[i + 1], "event_timestamp": cur_ts,
                    })
                    event_id += 1
                    stage_reached = i + 1
                else:
                    break

            if in_ab_window:
                ab_assignments.append({
                    "customer_id": cust["customer_id"], "session_id": session_id,
                    "test_name": "checkout_redesign_v2", "variant": variant,
                })

            # if purchase reached, create an order
            if stage_reached == len(FUNNEL_STAGES) - 1:
                n_items = random.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]
                chosen_products = random.sample(products, n_items)
                discount_pct = random.choices([0, 5, 10, 15, 20, 30], weights=[0.35, 0.15, 0.20, 0.15, 0.10, 0.05])[0]
                order_total = 0
                items_for_order = []
                for prod in chosen_products:
                    qty = random.choices([1, 2], weights=[0.85, 0.15])[0]
                    unit_price = prod["list_price"]
                    items_for_order.append((prod["product_id"], qty, unit_price))
                    order_total += qty * unit_price
                order_total = round(order_total * (1 - discount_pct / 100), 2)

                status = random.choices(
                    ["Delivered", "Delivered", "Delivered", "Returned", "Cancelled"],
                    weights=[0.70, 0.15, 0.05, 0.07, 0.03]
                )[0]

                orders.append({
                    "order_id": order_id,
                    "customer_id": cust["customer_id"],
                    "session_id": session_id,
                    "order_date": candidate_date,
                    "order_status": status,
                    "payment_method": weighted_choice(PAYMENT_METHODS, PAYMENT_WEIGHTS),
                    "discount_pct": discount_pct,
                    "total_amount": order_total,
                })
                for pid_, qty, price in items_for_order:
                    order_items.append({
                        "order_item_id": order_item_id, "order_id": order_id,
                        "product_id": pid_, "quantity": qty, "unit_price": price,
                    })
                    order_item_id += 1
                order_id += 1

            session_id += 1

    # ---- marketing spend by channel/month ----
    marketing_spend = []
    months = []
    cur = dt.date(START_DATE.year, START_DATE.month, 1)
    while cur <= END_DATE:
        months.append(cur)
        if cur.month == 12:
            cur = dt.date(cur.year + 1, 1, 1)
        else:
            cur = dt.date(cur.year, cur.month + 1, 1)

    for month in months:
        for ch in CHANNELS:
            if ch in ("Organic Search", "Direct", "Referral"):
                spend = 0  # unpaid channels
            else:
                base = {"Paid Social": 380000, "Paid Search": 420000,
                        "Affiliate": 140000, "Email": 45000}[ch]
                spend = round(base * random.uniform(0.75, 1.3))
            impressions = int(spend / random.uniform(0.15, 0.35)) if spend else random.randint(50000, 200000)
            clicks = int(impressions * random.uniform(0.01, 0.045))
            marketing_spend.append({
                "month": month, "channel": ch, "spend_inr": spend,
                "impressions": impressions, "clicks": clicks,
            })

    # ---- write CSVs ----
    def write_csv(filename, rows, fieldnames):
        with open(f"{OUT_DIR}/{filename}", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows):>7} rows -> {filename}")

    write_csv("customers.csv", customers,
               ["customer_id", "signup_date", "city", "acquisition_channel", "gender", "age_group"])
    write_csv("products.csv", products,
               ["product_id", "category", "sub_category", "brand", "list_price", "unit_cost"])
    write_csv("sessions.csv", sessions,
               ["session_id", "customer_id", "session_date", "device", "channel"])
    write_csv("funnel_events.csv", funnel_events,
               ["event_id", "session_id", "customer_id", "event_type", "event_timestamp"])
    write_csv("orders.csv", orders,
               ["order_id", "customer_id", "session_id", "order_date", "order_status",
                "payment_method", "discount_pct", "total_amount"])
    write_csv("order_items.csv", order_items,
               ["order_item_id", "order_id", "product_id", "quantity", "unit_price"])
    write_csv("marketing_spend.csv", marketing_spend,
               ["month", "channel", "spend_inr", "impressions", "clicks"])
    write_csv("ab_test_assignments.csv", ab_assignments,
               ["customer_id", "session_id", "test_name", "variant"])

    print("\nDone. Total customers:", len(customers), "| sessions:", len(sessions),
          "| funnel_events:", len(funnel_events), "| orders:", len(orders))


if __name__ == "__main__":
    main()
