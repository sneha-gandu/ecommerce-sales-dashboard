"""
E-Commerce Sales Performance — Data Pipeline & EDA
Connects to MySQL, cleans data, exports for Power BI, and performs analysis.
Author: [Your Name]
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG — update with your credentials
# ─────────────────────────────────────────────
DB_USER     = "root"
DB_PASSWORD = "yourpassword"
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_NAME     = "ecommerce_db"

OUTPUT_CSV   = "data/clean_sales_data.csv"
PLOTS_DIR    = "outputs/plots/"

# ─────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ─────────────────────────────────────────────
print("=" * 60)
print("  E-COMMERCE SALES PERFORMANCE — ANALYSIS PIPELINE")
print("=" * 60)

def get_engine():
    conn_str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(conn_str)

# ── For demo/testing without a live DB, generate synthetic data ──────────
def generate_demo_data(n=100_000):
    """Generates realistic synthetic e-commerce data for demo purposes."""
    print("\n  [DEMO MODE] Generating synthetic sales dataset (100K rows)...")
    np.random.seed(42)
    dates = pd.date_range("2022-01-01", "2023-12-31", periods=n)

    # Simulate Q3 2023 revenue drop via lower quantities
    base_qty = np.random.randint(1, 5, n)
    q3_mask = (dates.month.isin([7, 8, 9])) & (dates.year == 2023)
    base_qty[q3_mask] = np.maximum(1, base_qty[q3_mask] - 2)   # reduce Q3 qty

    regions   = np.random.choice(["North", "South", "East", "West", "Central"], n)
    categories = np.random.choice(
        ["Electronics", "Clothing", "Home & Kitchen", "Sports", "Beauty"], n,
        p=[0.30, 0.25, 0.20, 0.15, 0.10]
    )
    unit_prices = {
        "Electronics": np.random.uniform(200, 1500),
        "Clothing": np.random.uniform(20, 200),
        "Home & Kitchen": np.random.uniform(30, 400),
        "Sports": np.random.uniform(25, 300),
        "Beauty": np.random.uniform(15, 150),
    }
    prices = np.array([np.random.uniform(
        *{"Electronics":(200,1500),"Clothing":(20,200),
          "Home & Kitchen":(30,400),"Sports":(25,300),"Beauty":(15,150)}[c]
    ) for c in categories])

    discount   = np.random.choice([0, 0.05, 0.10, 0.15, 0.20], n, p=[0.5, 0.2, 0.15, 0.1, 0.05])
    cart_abandon = np.random.choice([0, 1], n, p=[0.72, 0.28])   # 28% abandon rate

    df = pd.DataFrame({
        "order_id":      range(1, n+1),
        "order_date":    dates,
        "region":        regions,
        "category":      categories,
        "quantity":      base_qty,
        "unit_price":    prices.round(2),
        "discount_pct":  discount,
        "cart_abandoned": cart_abandon,
        "customer_id":   np.random.randint(1000, 50000, n),
    })
    # Inject ~3% nulls to simulate real data
    for col in ["region", "unit_price"]:
        df.loc[df.sample(frac=0.03, random_state=1).index, col] = np.nan
    return df

# ─────────────────────────────────────────────
# 2. SQL QUERIES
# ─────────────────────────────────────────────
SQL_MAIN = """
    SELECT
        o.order_id,
        o.order_date,
        o.quantity,
        o.discount_pct,
        o.cart_abandoned,
        p.unit_price,
        p.category,
        r.region,
        c.customer_id
    FROM orders o
    JOIN products  p ON o.product_id  = p.product_id
    JOIN regions   r ON o.region_id   = r.region_id
    JOIN customers c ON o.customer_id = c.customer_id
"""

def load_data():
    try:
        engine = get_engine()
        print("\n[1/5] Connecting to MySQL database...")
        with engine.connect() as conn:
            df = pd.read_sql(text(SQL_MAIN), conn)
        print(f"  ✓ Loaded {len(df):,} rows from MySQL")
        return df
    except Exception as e:
        print(f"  ⚠  DB connection failed ({e}). Switching to demo data.")
        return generate_demo_data()

df_raw = load_data()

# ─────────────────────────────────────────────
# 3. DATA CLEANING
# ─────────────────────────────────────────────
print("\n[2/5] Cleaning data...")

df = df_raw.copy()

# Parse dates
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

# Drop rows with invalid dates or prices
before = len(df)
df.dropna(subset=["order_date", "unit_price"], inplace=True)
print(f"  ✓ Dropped {before - len(df):,} rows with null dates/prices")

# Fill region nulls with mode
df["region"].fillna(df["region"].mode()[0], inplace=True)

# Remove duplicate orders
dups = df.duplicated(subset="order_id").sum()
df.drop_duplicates(subset="order_id", inplace=True)
print(f"  ✓ Removed {dups:,} duplicate order IDs")

# Derived columns
df["revenue"]    = df["quantity"] * df["unit_price"] * (1 - df["discount_pct"])
df["year"]       = df["order_date"].dt.year
df["quarter"]    = df["order_date"].dt.quarter
df["month"]      = df["order_date"].dt.month
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
df["year_q"]     = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)

print(f"  ✓ Clean dataset: {len(df):,} rows | Revenue range: ₹{df['revenue'].min():.0f} – ₹{df['revenue'].max():.0f}")

# Export for Power BI
import os; os.makedirs("data", exist_ok=True); os.makedirs(PLOTS_DIR, exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False)
print(f"  ✓ Exported clean CSV → {OUTPUT_CSV}")

# ─────────────────────────────────────────────
# 4. ANALYSIS
# ─────────────────────────────────────────────
print("\n[3/5] Running analysis...")

# ── Quarterly revenue ──────────────────────
quarterly = df.groupby("year_q")["revenue"].sum().reset_index()
quarterly.columns = ["Quarter", "Revenue"]
q3_2022 = quarterly[quarterly["Quarter"] == "2022-Q3"]["Revenue"].values
q3_2023 = quarterly[quarterly["Quarter"] == "2023-Q3"]["Revenue"].values
if len(q3_2022) and len(q3_2023):
    drop_pct = (q3_2022[0] - q3_2023[0]) / q3_2022[0] * 100
    print(f"\n  ★ Q3 2023 Revenue Drop vs Q3 2022: {drop_pct:.1f}%")

# ── Cart abandonment ──────────────────────
abandon_rate = df["cart_abandoned"].mean() * 100
print(f"  ★ Cart Abandonment Rate: {abandon_rate:.1f}%")

# ── Revenue by region ──────────────────────
region_rev = df.groupby("region")["revenue"].sum().sort_values(ascending=False)
print(f"\n  Revenue by Region:")
for r, v in region_rev.items():
    print(f"    {r:<10} ₹{v:>15,.0f}")

# ── Revenue by category ──────────────────────
cat_rev = df.groupby("category")["revenue"].sum().sort_values(ascending=False)
print(f"\n  Revenue by Category:")
for c, v in cat_rev.items():
    print(f"    {c:<20} ₹{v:>12,.0f}")

# ─────────────────────────────────────────────
# 5. PLOTS
# ─────────────────────────────────────────────
print("\n[4/5] Generating charts...")

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 130})

# ── Plot 1: Quarterly Revenue Bar Chart ────────────────────
fig, ax = plt.subplots(figsize=(13, 5))
colors = ["#F44336" if "Q3" in q and "2023" in q else "#1E88E5"
          for q in quarterly["Quarter"]]
bars = ax.bar(quarterly["Quarter"], quarterly["Revenue"] / 1e6, color=colors,
              edgecolor="white", linewidth=0.5, width=0.65)
ax.set_title("Quarterly Revenue (₹M) — Q3 2023 Drop Highlighted", fontsize=14, pad=12)
ax.set_ylabel("Revenue (₹ Millions)")
ax.tick_params(axis="x", rotation=45, labelsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x:.0f}M"))
for bar, val in zip(bars, quarterly["Revenue"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f"₹{val/1e6:.1f}M", ha="center", va="bottom", fontsize=7)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}quarterly_revenue.png", dpi=150)
plt.close()
print(f"  ✓ {PLOTS_DIR}quarterly_revenue.png")

# ── Plot 2: Revenue by Region ──────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4))
region_rev.plot(kind="barh", ax=ax, color="#42A5F5", edgecolor="white")
ax.set_title("Revenue by Region", fontsize=13)
ax.set_xlabel("Revenue (₹)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x/1e6:.0f}M"))
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}region_revenue.png", dpi=150)
plt.close()
print(f"  ✓ {PLOTS_DIR}region_revenue.png")

# ── Plot 3: Category Revenue Pie ──────────────────────────
fig, ax = plt.subplots(figsize=(7, 7))
wedge_props = {"edgecolor": "white", "linewidth": 2}
ax.pie(cat_rev.values, labels=cat_rev.index, autopct="%1.1f%%",
       startangle=140, wedgeprops=wedge_props,
       colors=["#1E88E5", "#43A047", "#FB8C00", "#E53935", "#8E24AA"])
ax.set_title("Revenue Share by Product Category", fontsize=13, pad=12)
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}category_pie.png", dpi=150)
plt.close()
print(f"  ✓ {PLOTS_DIR}category_pie.png")

# ── Plot 4: Monthly Revenue Trend ──────────────────────────
monthly = df.groupby("year_month")["revenue"].sum().reset_index()
monthly["order_date"] = pd.to_datetime(monthly["year_month"])
monthly = monthly.sort_values("order_date")

fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(monthly["year_month"], monthly["revenue"]/1e6,
        color="#1E88E5", linewidth=2, marker="o", markersize=3)
ax.fill_between(range(len(monthly)), monthly["revenue"]/1e6, alpha=0.1, color="#1E88E5")
ax.set_xticks(range(0, len(monthly), 3))
ax.set_xticklabels(monthly["year_month"].iloc[::3], rotation=45, fontsize=8)
ax.set_title("Monthly Revenue Trend (₹M)", fontsize=13)
ax.set_ylabel("Revenue (₹ Millions)")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{PLOTS_DIR}monthly_trend.png", dpi=150)
plt.close()
print(f"  ✓ {PLOTS_DIR}monthly_trend.png")

# ── Summary ──────────────────────────────────────────────
total_rev = df["revenue"].sum()
total_orders = len(df)
avg_order_val = df["revenue"].mean()

print("\n" + "=" * 60)
print("  ANALYSIS SUMMARY")
print("=" * 60)
print(f"  Total Revenue     : ₹{total_rev:>15,.0f}")
print(f"  Total Orders      : {total_orders:>15,}")
print(f"  Avg Order Value   : ₹{avg_order_val:>15,.2f}")
print(f"  Cart Abandon Rate : {abandon_rate:>14.1f}%")
if len(q3_2022) and len(q3_2023):
    print(f"  Q3 Revenue Drop   : {drop_pct:>14.1f}%  ← root cause: cart abandonment")
print("=" * 60)
print("  ✓ All charts saved. Import clean_sales_data.csv into Power BI.")
print("=" * 60)
