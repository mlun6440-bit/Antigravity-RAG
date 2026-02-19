import sqlite3

conn = sqlite3.connect('data/assets.db')
cursor = conn.cursor()

# Get total count of unique categories
cursor.execute('SELECT COUNT(DISTINCT Category) FROM assets')
total_categories = cursor.fetchone()[0]

print(f'Total unique categories: {total_categories}\n')

# Get breakdown by category
cursor.execute('SELECT Category, COUNT(*) FROM assets GROUP BY Category ORDER BY COUNT(*) DESC')
print('Categories breakdown:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} assets')

conn.close()
