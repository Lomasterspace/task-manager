# app.py
from flask import Flask, render_template, request, redirect, url_for
import os
import psycopg2

app = Flask(__name__)

# Обязательно используем DATABASE_URL из Render
DATABASE_URL = os.environ['DATABASE_URL']  # Без fallback

def get_db_connection():
    # Подключаемся к PostgreSQL с SSL
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Создаём таблицу при запуске
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = request.form['title'].strip()
        if title:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO tasks (title, done) VALUES (%s, %s)', (title, False))
            conn.commit()
            cur.close()
            conn.close()
        return redirect(url_for('index'))

    # Получаем все задачи
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, done FROM tasks ORDER BY id')
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', tasks=tasks)

@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT done FROM tasks WHERE id = %s', (task_id,))
    done = cur.fetchone()
    if done is not None:
        cur.execute('UPDATE tasks SET done = %s WHERE id = %s', (not done[0], task_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    # Render сам укажет PORT, по умолчанию 10000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)