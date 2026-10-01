import sqlite3

conn = sqlite3.connect("storage/sample.db")
conn.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount INTEGER,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
""")
conn.execute("INSERT INTO orders (customer_id, amount, status) VALUES (1, 500, 'PAID')")
conn.execute("INSERT INTO orders (customer_id, amount, status) VALUES (1, 300, 'PAID')")
conn.execute("INSERT INTO orders (customer_id, amount, status) VALUES (2, 100, 'PENDING')")
conn.commit()
conn.close()
print("done")