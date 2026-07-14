import sqlite3

conn = sqlite3.connect('logbook.db')
cursor = conn.cursor()

# Inserting two test users (we are using plain text passwords for this prototype to keep friction low)
cursor.execute("INSERT INTO Users (username, password_hash, role) VALUES ('admin', 'password123', 'Admin')")
cursor.execute("INSERT INTO Users (username, password_hash, role) VALUES ('worker', 'password123', 'User')")

conn.commit()
conn.close()

print("Test users created! You can now log in with the username 'admin' or 'worker' (Password: password123)")