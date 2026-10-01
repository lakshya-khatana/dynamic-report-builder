import sqlite3

conn = sqlite3.connect("storage/sample.db")
result = conn.execute("SELECT sql FROM sqlite_master WHERE name='orders'").fetchone()
print(result)
conn.close()