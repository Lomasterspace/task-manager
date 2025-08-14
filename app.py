# app.py
from flask import Flask, render_template, request, redirect, url_for
import os
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.environ.get('DATABASE_URL', 'dbname=taskmanager')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            );
        ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = request.form['title'].strip()
        if title:
            conn = get_db_connection()
            conn.cursor().execute('INSERT INTO tasks (title, done) VALUES (%s, %s)', (title, False))
            conn.commit()
            conn.close()
        return redirect(url_for('index'))

    # Получаем задачи
    conn = get_db_connection()
    conn.cursor().execute('SELECT id, title, done FROM tasks ORDER BY id')
    tasks = conn.cursor().fetchall()
    conn.close()

    return render_template('index.html', tasks=tasks)

@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT done FROM tasks WHERE id = %s', (task_id,))
    done = cur.fetchone()
    if done:
        cur.execute('UPDATE tasks SET done = %s WHERE id = %s', (not done[0], task_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    conn = get_db_connection()
    conn.cursor().execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))