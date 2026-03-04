-- PostgreSQL initialization script.
-- Creates sample tables and a read-only user for the NL2SQL agent.

-- ── Sample Schema ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    email       VARCHAR(200) UNIQUE NOT NULL,
    region      VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    product_id     SERIAL PRIMARY KEY,
    name           VARCHAR(300) NOT NULL,
    category_id    INT,
    price          NUMERIC(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id    SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    employee_id INT,
    amount      NUMERIC(12, 2) NOT NULL,
    status      VARCHAR(50) DEFAULT 'pending',
    region      VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id      INT REFERENCES orders(order_id),
    product_id    INT REFERENCES products(product_id),
    quantity      INT NOT NULL,
    unit_price    NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    department_id SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id   SERIAL PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    email         VARCHAR(200),
    department_id INT REFERENCES departments(department_id),
    salary        NUMERIC(10, 2),
    last_login    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS users (
    user_id    SERIAL PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    email      VARCHAR(200) UNIQUE NOT NULL,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Read-only user ────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_pass';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE mydb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- ── Sample Data ───────────────────────────────────────────────
INSERT INTO categories (category_name) VALUES ('Electronics'), ('Clothing'), ('Books'), ('Home & Garden') ON CONFLICT DO NOTHING;
INSERT INTO departments (name) VALUES ('Engineering'), ('Sales'), ('Marketing'), ('HR') ON CONFLICT DO NOTHING;

INSERT INTO customers (name, email, region) VALUES
  ('Alice Johnson', 'alice@example.com', 'North'),
  ('Bob Smith', 'bob@example.com', 'South'),
  ('Carol White', 'carol@example.com', 'East'),
  ('David Lee', 'david@example.com', 'West')
ON CONFLICT DO NOTHING;

INSERT INTO products (name, category_id, price, stock_quantity) VALUES
  ('Laptop Pro 15', 1, 1299.99, 50),
  ('Wireless Mouse', 1, 29.99, 200),
  ('Python Cookbook', 3, 49.99, 0),
  ('Winter Jacket', 2, 149.99, 30)
ON CONFLICT DO NOTHING;
