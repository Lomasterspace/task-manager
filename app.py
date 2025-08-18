# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import psycopg2
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Замени на случайную строку

# Используем DATABASE_URL из Render
DATABASE_URL = os.environ['DATABASE_URL']

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Пользователи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    ''')
    # Задачи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE,
            priority TEXT NOT NULL DEFAULT 'low',
            due_date TIMESTAMP,
            user_id INTEGER REFERENCES users(id),
            file_data BYTEA,
            file_name TEXT
        );
    ''')
    # Сообщения
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            sender_id INTEGER REFERENCES users(id),
            receiver_id INTEGER REFERENCES users(id),
            content TEXT NOT NULL,
            task_id INTEGER REFERENCES tasks(id),
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        priority = request.form.get('priority', 'low')
        due_date = request.form.get('due_date') or None
        file_data = None
        file_name = None

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and '.' in file.filename:
                file_data = file.read()
                file_name = secure_filename(file.filename)

        if title:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO tasks (title, done, priority, due_date, user_id, file_data, file_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (title, False, priority, due_date, session['user_id'], file_data, file_name))
            conn.commit()
            cur.close()
            conn.close()
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, title, done, priority, due_date, file_name FROM tasks 
        WHERE user_id = %s ORDER BY id
    ''', (session['user_id'],))
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', tasks=tasks)

@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET done = NOT done WHERE id = %s AND user_id = %s', (task_id, session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (task_id, session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/download/<int:task_id>')
def download_file(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT file_data, file_name FROM tasks WHERE id = %s AND user_id = %s', (task_id, session['user_id']))
    data = cur.fetchone()
    cur.close()
    conn.close()
    if data and data[0]:
        file_data, file_name = data
        return app.response_class(file_data, mimetype='application/octet-stream',
                                  headers={'Content-Disposition': f'attachment; filename={file_name}'})
    flash("Файл не найден.")
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, password FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and user[1] == password:
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        flash("Неверный логин или пароль.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash("Заполните все поля.")
            return redirect(url_for('register'))
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, password))
            conn.commit()
            flash("Регистрация успешна! Войдите.")
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash("Пользователь с таким именем уже существует.")
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE id != %s", (session['user_id'],))
    users = cur.fetchall()
    cur.execute('''
        SELECT m.content, m.created_at, u1.username as sender, u2.username as receiver 
        FROM messages m
        JOIN users u1 ON m.sender_id = u1.id
        JOIN users u2 ON m.receiver_id = u2.id
        WHERE m.sender_id = %s OR m.receiver_id = %s
        ORDER BY m.created_at
    ''', (session['user_id'], session['user_id']))
    msgs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('messages.html', users=users, messages=msgs)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    receiver_id = request.form['receiver_id']
    content = request.form['content'].strip()
    if content and receiver_id:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO messages (sender_id, receiver_id, content)
            VALUES (%s, %s, %s)
        ''', (session['user_id'], receiver_id, content))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for('messages'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)