import sqlite3

conn = sqlite3.connect('data/assets.db')
cursor = conn.cursor()

print("Checking 'Category' column for electrical items:")
cursor.execute("SELECT DISTINCT Category FROM assets WHERE Category LIKE '%Electrical%' OR Category LIKE '%Distribution%' LIMIT 50")
categories = [row[0] for row in cursor.fetchall()]

for cat in categories:
    print(f" - {cat}")

print("\nChecking if specific term exists:")
term = "Electrical Systems,Distribution Board"
cursor.execute("SELECT COUNT(*) FROM assets WHERE Category = ?", (term,))
count = cursor.fetchone()[0]
print(f"Exact match count for '{term}': {count}")

conn.close()
