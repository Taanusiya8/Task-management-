from flask import Flask, jsonify, request, session, send_from_directory
import sqlite3, os, hashlib, secrets
from datetime import datetime, timedelta
import re

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'task_manager.db')
FRONTEND = os.path.join(BASE, 'frontend')
app = Flask(__name__, static_folder='frontend')
app.secret_key = os.environ.get('SECRET_KEY', 'task-manager-dev-secret-change-me')
app.permanent_session_lifetime = timedelta(days=7)


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      salt TEXT NOT NULL,
      notifications_enabled INTEGER DEFAULT 1,
      dark_theme INTEGER DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      category TEXT DEFAULT 'Other',
      priority TEXT DEFAULT 'Medium',
      due_date TEXT DEFAULT '',
      due_time TEXT DEFAULT '',
      status TEXT DEFAULT 'To Do',
      created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')
    conn.commit(); conn.close()


def valid_email(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email))


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
    return digest, salt


def current_user():
    uid = session.get('user_id')
    if not uid: return None
    conn = db(); user = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone(); conn.close()
    return user


def task_dict(row):
    return {
      'id': row['id'], 'title': row['title'], 'description': row['description'],
      'category': row['category'], 'priority': row['priority'],
      'dueDate': row['due_date'], 'dueTime': row['due_time'], 'status': row['status'],
      'createdDate': row['created_at']
    }


def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return jsonify({'error':'Authentication required'}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.get('/')
def index(): return send_from_directory(FRONTEND, 'index.html')

@app.get('/<path:path>')
def frontend(path):
    return send_from_directory(FRONTEND, path)

@app.post('/api/register')
def register():
    data = request.get_json() or {}
    name, email, password = data.get('name','').strip(), data.get('email','').strip().lower(), data.get('password','')
    if not name or not valid_email(email) or len(password) < 6: return jsonify({'error':'Enter a valid name and email, and a password of at least 6 characters'}), 400
    pwd, salt = hash_password(password)
    conn = db()
    try:
        cur = conn.execute('INSERT INTO users(name,email,password_hash,salt,created_at) VALUES(?,?,?,?,?)', (name,email,pwd,salt,datetime.utcnow().isoformat()))
        conn.commit(); uid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close(); return jsonify({'error':'An account with this email already exists'}), 409
    conn.close(); session.permanent=True; session['user_id']=uid
    return jsonify({'message':'Account created successfully','user':{'id':uid,'name':name,'email':email}}), 201

@app.post('/api/login')
def login():
    data=request.get_json() or {}; email=data.get('email','').strip().lower(); password=data.get('password','')
    conn=db(); user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); conn.close()
    if not user: return jsonify({'error':'Invalid email or password'}), 401
    digest,_=hash_password(password,user['salt'])
    if not secrets.compare_digest(digest,user['password_hash']): return jsonify({'error':'Invalid email or password'}), 401
    session.permanent=True; session['user_id']=user['id']
    return jsonify({'message':'Login successful','user':{'id':user['id'],'name':user['name'],'email':user['email']}})

@app.post('/api/logout')
def logout(): session.clear(); return jsonify({'message':'Logged out'})

@app.get('/api/me')
def me():
    user=current_user()
    if not user: return jsonify({'authenticated':False})
    return jsonify({'authenticated':True,'user':{'id':user['id'],'name':user['name'],'email':user['email'], 'notificationsEnabled':bool(user['notifications_enabled']), 'darkTheme':bool(user['dark_theme'])}})

@app.get('/api/tasks')
@login_required
def get_tasks():
    user=current_user(); conn=db(); rows=conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY CASE WHEN due_date="" THEN 1 ELSE 0 END, due_date, due_time, id DESC',(user['id'],)).fetchall(); conn.close()
    return jsonify([task_dict(r) for r in rows])

@app.post('/api/tasks')
@login_required
def create_task():
    data=request.get_json() or {}; user=current_user()
    if not data.get('title','').strip(): return jsonify({'error':'Task title is required'}),400
    conn=db(); cur=conn.execute('INSERT INTO tasks(user_id,title,description,category,priority,due_date,due_time,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)', (user['id'],data['title'].strip(),data.get('description',''),data.get('category','Other'),data.get('priority','Medium'),data.get('dueDate',''),data.get('dueTime',''),data.get('status','To Do'),datetime.utcnow().isoformat())); conn.commit(); row=conn.execute('SELECT * FROM tasks WHERE id=?',(cur.lastrowid,)).fetchone(); conn.close()
    return jsonify(task_dict(row)),201

@app.put('/api/tasks/<int:task_id>')
@login_required
def update_task(task_id):
    data=request.get_json() or {}; user=current_user(); conn=db()
    row=conn.execute('SELECT * FROM tasks WHERE id=? AND user_id=?',(task_id,user['id'])).fetchone()
    if not row: conn.close(); return jsonify({'error':'Task not found'}),404
    fields=['title','description','category','priority','due_date','due_time','status']; values=[data.get('title',row['title']),data.get('description',row['description']),data.get('category',row['category']),data.get('priority',row['priority']),data.get('dueDate',row['due_date']),data.get('dueTime',row['due_time']),data.get('status',row['status'])]
    conn.execute('UPDATE tasks SET title=?,description=?,category=?,priority=?,due_date=?,due_time=?,status=? WHERE id=? AND user_id=?', (*values,task_id,user['id'])); conn.commit(); row=conn.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone(); conn.close(); return jsonify(task_dict(row))

@app.delete('/api/tasks/<int:task_id>')
@login_required
def delete_task(task_id):
    user=current_user(); conn=db(); cur=conn.execute('DELETE FROM tasks WHERE id=? AND user_id=?',(task_id,user['id'])); conn.commit(); conn.close()
    if not cur.rowcount: return jsonify({'error':'Task not found'}),404
    return jsonify({'message':'Task deleted'})

@app.patch('/api/tasks/<int:task_id>/complete')
@login_required
def complete_task(task_id):
    user=current_user(); conn=db(); cur=conn.execute('UPDATE tasks SET status="Completed" WHERE id=? AND user_id=?',(task_id,user['id'])); conn.commit(); conn.close()
    if not cur.rowcount: return jsonify({'error':'Task not found'}),404
    return jsonify({'message':'Task completed'})

@app.put('/api/profile')
@login_required
def profile():
    data=request.get_json() or {}; user=current_user(); name=data.get('name',user['name']).strip(); email=data.get('email',user['email']).strip().lower()
    if not name or not valid_email(email): return jsonify({'error':'Enter a valid name and email'}),400
    conn=db()
    try: conn.execute('UPDATE users SET name=?,email=? WHERE id=?',(name,email,user['id'])); conn.commit()
    except sqlite3.IntegrityError: conn.close(); return jsonify({'error':'Email is already in use'}),409
    conn.close(); return jsonify({'message':'Profile updated successfully'})

@app.put('/api/settings')
@login_required
def settings():
    data=request.get_json() or {}; user=current_user(); n=1 if data.get('notificationsEnabled',True) else 0; d=1 if data.get('darkTheme',False) else 0
    conn=db(); conn.execute('UPDATE users SET notifications_enabled=?,dark_theme=? WHERE id=?',(n,d,user['id'])); conn.commit(); conn.close(); return jsonify({'message':'Settings saved'})

@app.put('/api/password')
@login_required
def password():
    data=request.get_json() or {}; new=data.get('password','')
    if len(new)<6: return jsonify({'error':'Password must be at least 6 characters'}),400
    pwd,salt=hash_password(new); user=current_user(); conn=db(); conn.execute('UPDATE users SET password_hash=?,salt=? WHERE id=?',(pwd,salt,user['id'])); conn.commit(); conn.close(); return jsonify({'message':'Password changed successfully'})

@app.get('/api/reports')
@login_required
def reports():
    user=current_user(); conn=db(); rows=conn.execute('SELECT * FROM tasks WHERE user_id=?',(user['id'],)).fetchall(); conn.close()
    now=datetime.now(); counts={'total':len(rows),'completed':0,'overdue':0,'inProgress':0,'todo':0}
    weekly=[]
    for r in rows:
        status=r['status']; effective=status
        if status!='Completed' and r['due_date']:
            try:
                due=datetime.fromisoformat(r['due_date']+'T'+(r['due_time'] or '23:59'))
                if due < now: effective='Overdue'
            except ValueError: pass
        if effective=='Completed': counts['completed']+=1
        elif effective=='Overdue': counts['overdue']+=1
        elif effective=='In Progress': counts['inProgress']+=1
        elif effective=='To Do': counts['todo']+=1
    counts['pending']=counts['total']-counts['completed']; counts['percentage']=round(counts['completed']/counts['total']*100) if counts['total'] else 0
    return jsonify(counts)

init_db()
if __name__=='__main__': app.run(debug=True, host='127.0.0.1', port=5000)
