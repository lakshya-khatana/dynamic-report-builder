import sqlite3

conn = sqlite3.connect("storage/sample.db")
conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")
conn.execute("INSERT INTO customers (name) VALUES ('Asha'), ('Ravi')")
conn.commit()
conn.close()
print("done")