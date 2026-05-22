-- ============================================================
--  E-Commerce Sales Performance — SQL Queries
--  Database: MySQL | Author: [Your Name]
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. CREATE SCHEMA (run once)
-- ─────────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INT PRIMARY KEY AUTO_INCREMENT,
    customer_name VARCHAR(100),
    email         VARCHAR(100),
    signup_date   DATE
);

CREATE TABLE IF NOT EXISTS regions (
    region_id   INT PRIMARY KEY AUTO_INCREMENT,
    region_name VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100),
    category     VARCHAR(50),
    unit_price   DECIMAL(10, 2)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      INT PRIMARY KEY AUTO_INCREMENT,
    customer_id   INT,
    product_id    INT,
    region_id     INT,
    order_date    DATE,
    quantity      INT,
    discount_pct  DECIMAL(4, 2) DEFAULT 0.00,
    cart_abandoned TINYINT(1) DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id),
    FOREIGN KEY (region_id)   REFERENCES regions(region_id)
);


-- ─────────────────────────────────────────────────────────────
-- 2. MAIN JOIN QUERY — Full denormalised sales table
-- ─────────────────────────────────────────────────────────────
SELECT
    o.order_id,
    o.order_date,
    YEAR(o.order_date)    AS year,
    QUARTER(o.order_date) AS quarter,
    MONTHNAME(o.order_date) AS month_name,
    o.quantity,
    p.unit_price,
    o.discount_pct,
    ROUND(o.quantity * p.unit_price * (1 - o.discount_pct), 2) AS revenue,
    o.cart_abandoned,
    p.category,
    r.region_name         AS region,
    c.customer_id
FROM orders o
JOIN products  p ON o.product_id  = p.product_id
JOIN regions   r ON o.region_id   = r.region_id
JOIN customers c ON o.customer_id = c.customer_id;


-- ─────────────────────────────────────────────────────────────
-- 3. QUARTERLY REVENUE AGGREGATION
-- ─────────────────────────────────────────────────────────────
SELECT
    YEAR(o.order_date)                                              AS year,
    QUARTER(o.order_date)                                           AS quarter,
    CONCAT(YEAR(o.order_date), '-Q', QUARTER(o.order_date))         AS year_quarter,
    COUNT(DISTINCT o.order_id)                                      AS total_orders,
    ROUND(SUM(o.quantity * p.unit_price * (1 - o.discount_pct)), 2) AS total_revenue,
    ROUND(AVG(o.quantity * p.unit_price * (1 - o.discount_pct)), 2) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY year, quarter
ORDER BY year, quarter;


-- ─────────────────────────────────────────────────────────────
-- 4. REVENUE BY REGION
-- ─────────────────────────────────────────────────────────────
SELECT
    r.region_name                                                    AS region,
    COUNT(DISTINCT o.order_id)                                       AS orders,
    ROUND(SUM(o.quantity * p.unit_price * (1 - o.discount_pct)), 2) AS revenue,
    ROUND(100.0 * SUM(o.quantity * p.unit_price * (1 - o.discount_pct)) /
          SUM(SUM(o.quantity * p.unit_price * (1 - o.discount_pct))) OVER (), 1) AS revenue_pct
FROM orders o
JOIN products p ON o.product_id = p.product_id
JOIN regions  r ON o.region_id  = r.region_id
GROUP BY region
ORDER BY revenue DESC;


-- ─────────────────────────────────────────────────────────────
-- 5. CART ABANDONMENT ANALYSIS
-- ─────────────────────────────────────────────────────────────
SELECT
    YEAR(order_date)                                   AS year,
    QUARTER(order_date)                                AS quarter,
    COUNT(*)                                           AS total_visits,
    SUM(cart_abandoned)                                AS abandoned,
    ROUND(100.0 * SUM(cart_abandoned) / COUNT(*), 1)   AS abandon_rate_pct
FROM orders
GROUP BY year, quarter
ORDER BY year, quarter;


-- ─────────────────────────────────────────────────────────────
-- 6. TOP 10 PRODUCTS BY REVENUE
-- ─────────────────────────────────────────────────────────────
SELECT
    p.product_name,
    p.category,
    COUNT(o.order_id)                                               AS units_sold,
    ROUND(SUM(o.quantity * p.unit_price * (1 - o.discount_pct)), 2) AS total_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;


-- ─────────────────────────────────────────────────────────────
-- 7. Q3 YoY COMPARISON (root cause investigation)
-- ─────────────────────────────────────────────────────────────
SELECT
    YEAR(o.order_date)                                              AS year,
    ROUND(SUM(o.quantity * p.unit_price * (1 - o.discount_pct)), 2) AS q3_revenue,
    ROUND(100.0 * SUM(cart_abandoned) / COUNT(*), 1)                AS abandon_rate_pct
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE QUARTER(o.order_date) = 3
GROUP BY year
ORDER BY year;
