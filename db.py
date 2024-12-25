import sqlite3

# Создаём соединение с базой данных
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
update users set type = 'a' where id = 1
""")

conn.commit()
conn.close()