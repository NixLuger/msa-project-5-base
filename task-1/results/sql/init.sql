CREATE DATABASE source OWNER airflow;

\connect source

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    amount      NUMERIC(10,2) NOT NULL,
    status      TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO orders (order_id, user_id, amount, status) VALUES
 (1,  101,  1500.00, 'paid'),
 (2,  102,   800.00, 'paid'),
 (3,  103,  2300.50, 'paid'),
 (4,  104,   450.00, 'paid'),
 (5,  105,  3100.00, 'paid'),
 (6,  106,   720.00, 'paid'),
 (7,  107,  1990.00, 'paid'),
 (8,  108,   610.00, 'paid'),
 (9,  109,  1220.00, 'paid'),
 (10, 110,  4400.00, 'paid'),
 (11, 111,   330.00, 'paid'),
 (12, 112,   980.00, 'paid'),
 (13, 113,  2560.00, 'paid'),
 (14, 114,   770.00, 'paid'),
 (15, 115,  1480.00, 'paid'),
 (16, 116,   540.00, 'paid'),
 (17, 117,  1320.00, 'paid'),
 (18, 118,   890.00, 'paid'),
 (19, 119,  2100.00, 'paid'),
 (20, 120,   610.00, 'paid');
