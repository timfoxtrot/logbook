import sqlite3

# This creates a new file called 'logbook.db' in your folder
conn = sqlite3.connect('logbook.db')
cursor = conn.cursor()

# Create the Users Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT
)
''')

# Create the Logs Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users (id)
)
''')

# Save and close
conn.commit()
conn.close()

print("Database and tables created successfully! The vibes are immaculate.")