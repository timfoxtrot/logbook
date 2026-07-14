from flask import Flask, render_template, request, redirect, url_for, session, Response, flash
import sqlite3
import csv
from datetime import datetime, timedelta
import io

app = Flask(__name__)
app.secret_key = 'super_secret_vibe_key' 

# NEW: Extracts ONLY the Date (GMT+10) for our headers
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%B %d, %Y at %I:%M %p (GMT+10)'):
    # This takes the raw ISO string '2026-07-14T13:52' 
    # and formats it as 'July 14, 2026 at 01:52 PM (GMT+10)'
    try:
        dt = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        return dt.strftime(format)
    except:
        return value

@app.template_filter('timeformat')
def timeformat(value):
    try:
        # Assumes input format YYYY-MM-DDTHH:MM
        dt = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        return dt.strftime('%I:%M %p')
    except:
        return value

from datetime import datetime

@app.template_filter('localdate')
def localdate(value):
    try:
        # Assumes input format YYYY-MM-DDTHH:MM
        dt = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        # %A = Full weekday name, %B = Full month name, %d = Day, %Y = Year
        return dt.strftime('%A, %B %d, %Y').upper() 
    except:
        return value

# NEW: Extracts ONLY the Time (GMT+10) for the individual logs
@app.template_filter('localtime')
def localtime(value):
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        local_dt = dt + timedelta(hours=10)
        return local_dt.strftime('%I:%M %p') # e.g., 10:15 AM
    except:
        return value

def get_db():
    conn = sqlite3.connect('logbook.db')
    conn.row_factory = sqlite3.Row # This lets us access columns by name
    return conn

@app.route('/')
def home():
    # If not logged in, send them to the login page
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # If logged in, fetch only THEIR draft logs
    conn = get_db()
    drafts = conn.execute(
        "SELECT * FROM Logs WHERE user_id = ? AND status = 'draft' ORDER BY timestamp, user_id", 
        (session['user_id'],)
    ).fetchall()
    conn.close()

    # Send the drafts to a new dashboard template
    return render_template('dashboard.html', drafts=drafts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        # Look up user by username
        user = conn.execute("SELECT * FROM Users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        # Verify password (Note: In a real app, use Werkzeug's check_password_hash)
        if user and user['password_hash'] == password:
            session.clear() # Clear any old session data
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session['role'] = user['role']
            
            return redirect(url_for('home')) # Redirect to your dashboard
        else:
            return "Invalid username or password. Please go back and try again."
            
    return render_template('login.html')

# NEW ROUTE: This handles the "Save Draft" button
@app.route('/save_draft', methods=['POST'])
def save_draft():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    content = request.form['content']
    # 1. Capture the timestamp from the form
    timestamp = request.form['timestamp'] 
    
    # 2. Insert the new log as a draft, including the timestamp
    conn = get_db()
    conn.execute(
        "INSERT INTO Logs (user_id, content, timestamp, status) VALUES (?, ?, ?, 'draft')", 
        (session['user_id'], content, timestamp) # Added 'timestamp' here
    )
    conn.commit()
    conn.close()
    
    # Refresh the page
    return redirect(url_for('home'))

# NEW ROUTE: This handles committing the shift
@app.route('/commit_shift', methods=['POST'])
def commit_shift():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Update all drafts for this user to 'committed'
    conn = get_db()
    conn.execute(
        "UPDATE Logs SET status = 'committed' WHERE user_id = ? AND status = 'draft'", 
        (session['user_id'],)
    )
    conn.commit()
    conn.close()
    
    # Refresh the page
    return redirect(url_for('home'))

# UPDATED ROUTE: The Master Log (with Date Filters)
@app.route('/master_log')
def master_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    search_query = request.args.get('q', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    conn = get_db()
    
    # We build the SQL query dynamically based on what the user filled out
    query = '''
        SELECT Logs.timestamp, Logs.content, Users.username, Users.first_name, Users.last_name
        FROM Logs JOIN Users ON Logs.user_id = Users.id 
        WHERE Logs.status = 'committed'
    '''
    params = []
    
    if search_query:
        query += " AND (Logs.content LIKE ? OR Users.username LIKE ?)"
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
        
    if start_date:
        # SQLite adjusts the UTC time to GMT+10 before checking the date!
        query += " AND DATE(datetime(Logs.timestamp, '+10 hours')) >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND DATE(datetime(Logs.timestamp, '+10 hours')) <= ?"
        params.append(end_date)
        
    query += " ORDER BY Logs.timestamp DESC"
    
    logs = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('master_log.html', logs=logs, search_query=search_query, start_date=start_date, end_date=end_date)

# NEW ROUTE: Delete a draft
@app.route('/delete_draft/<int:draft_id>', methods=['POST'])
def delete_draft(draft_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    # We check user_id to ensure a user can only delete THEIR OWN drafts
    conn.execute(
        "DELETE FROM Logs WHERE id = ? AND user_id = ? AND status = 'draft'", 
        (draft_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

# UPDATED ROUTE: Export to CSV (Now respects date filters)
@app.route('/export_csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # NEW: Admin check!
    if session.get('role') != 'Admin':
        return "Access Denied. Only Admins can export the Master Log."
        
    search_query = request.args.get('q', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    conn = get_db()
    
    # Rebuilding the exact same query for the export
    query = '''
        SELECT Logs.timestamp, Logs.content, Users.username 
        FROM Logs JOIN Users ON Logs.user_id = Users.id 
        WHERE Logs.status = 'committed'
    '''
    params = []
    
    if search_query:
        query += " AND (Logs.content LIKE ? OR Users.username LIKE ?)"
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    if start_date:
        query += " AND DATE(datetime(Logs.timestamp, '+10 hours')) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND DATE(datetime(Logs.timestamp, '+10 hours')) <= ?"
        params.append(end_date)
        
    query += " ORDER BY Logs.timestamp DESC"
    
    logs = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Author', 'Log Content'])
    
    for log in logs:
        try:
            dt = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
            local_dt = dt + timedelta(hours=10)
            csv_time = local_dt.strftime('%B %d, %Y at %I:%M %p (GMT+10)')
        except:
            csv_time = log['timestamp'] 

        writer.writerow([csv_time, log['username'], log['content']])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=master_log.csv"}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# NEW ROUTE: Manage Users (Admin Only)
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    # Security check: Only Admins can enter
    if session.get('role') != 'Admin':
        flash("Access Denied.")
        return redirect(url_for('dashboard'))

    conn = get_db()
    
    # Handle user creation (Your existing logic)
    if request.method == 'POST':
        # Ensure we only process if the form is for a user
        if 'username' in request.form:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form['username']
            password = "Giaa2026!" # Default password
            role = request.form['role']
            conn.execute(
                "INSERT INTO Users (username, password_hash, role, first_name, last_name) VALUES (?, ?, ?, ?, ?)", 
                (username, password, role, first_name, last_name)
            )
            conn.commit()
            flash("User created successfully!")

    users = conn.execute("SELECT * FROM Users").fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', users=users)

# NEW ROUTE: Delete a User
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'Admin':
        return "Access Denied."
    conn = get_db()
    conn.execute("DELETE FROM Users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_users'))

from flask import Flask, render_template, request, redirect, url_for, session, flash
# Ensure your get_db function is available in this file as well

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    # 1. Ensure user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        
        # 2. Update the database
        conn = get_db()
        try:
            conn.execute("UPDATE Users SET password_hash = ? WHERE id = ?", 
                         (new_password, session['user_id']))
            conn.commit()
        except Exception as e:
            print(f"Error updating password: {e}")
            flash('An error occurred. Please try again.')
            return redirect(url_for('change_password'))
        finally:
            conn.close()
        
        # 3. Flash the success banner
        flash('Success! Please log in with your new credentials.')
        
        # 4. Log the user out for security
        session.clear()
        
        # 5. Redirect to login
        return redirect(url_for('login'))
        
    return render_template('change_password.html')

@app.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    if session.get('role') != 'Admin':
        return "Unauthorized", 403
        
    conn = get_db()
    # Replace 'Giaa2026!' with whatever default you prefer
    conn.execute("UPDATE Users SET password_hash = ? WHERE id = ?", 
                 ('Giaa2026!', user_id))
    conn.commit()
    conn.close()
    
    # Optional: Flash a message to confirm
    flash(f'Password has been reset to "Giaa2026!" for user ID {user_id}')
    return redirect(url_for('manage_users'))

@app.route('/purge_logs', methods=['POST'])
def purge_logs():
    # Double-check security: ONLY let admins do this
    if session.get('role') != 'Admin':
        return "Unauthorized", 403

    conn = get_db()
    # Deletes all logs marked as 'committed'
    conn.execute("DELETE FROM Logs WHERE status = 'committed'")
    conn.commit()
    conn.close()
    
    flash("Master logs have been purged.", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)