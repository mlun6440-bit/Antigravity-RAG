import sqlite3

conn = sqlite3.connect('data/assets.db')
cursor = conn.cursor()
cursor.execute("SELECT data_source, COUNT(*) FROM assets GROUP BY data_source ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(row)
conn.close()
