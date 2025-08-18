# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import psycopg2
from werkzeug.utils import secure_filename

# Список разрешённых расширений
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'xlsx'}

def allowed_file(filename):
    """
    Проверяет, имеет ли файл разрешённое расширение.
    filename: имя файла, например, 'отчёт.pdf'
    Возвращает: True, если расширение разрешено, иначе False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'суперсекретныйключ'  # Замени на случайную строку

# Используем DATABASE_URL из Render
DATABASE_URL = os.environ['DATABASE_URL']

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Создаём таблицы (если ещё не созданы)
    # =======================================

    # Пользователи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'executor', -- 'admin', 'manager', 'executor'
            manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # Задачи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'new', -- 'new', 'in_progress', 'done'
            priority TEXT NOT NULL DEFAULT 'low', -- 'low', 'medium', 'high'
            due_date TIMESTAMP,
            created_by INTEGER REFERENCES users(id),
            assigned_to INTEGER REFERENCES users(id),
            project_id INTEGER REFERENCES projects(id),
            file_data BYTEA,
            file_name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # Проекты
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            manager_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # Комментарии
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # История изменений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id SERIAL PRIMARY KEY,
            task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL, -- 'created', 'assigned', 'status_changed'
            details TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # Уведомления
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            message TEXT NOT NULL,
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            link TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    ''')

    # Переписка
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
    cur.execute('''
           ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
       ''')

    # 2. Добавляем колонки, если их нет (для совместимости с старыми данными)
    # =====================================================================

    # Колонки для users
    cur.execute('''
        ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'executor';
    ''')
    cur.execute('''
        ALTER TABLE users ADD COLUMN IF NOT EXISTS manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
    ''')
    # Колонки для tasks
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'new';
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'low';
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date TIMESTAMP;
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assigned_to INTEGER REFERENCES users(id);
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id);
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS file_data BYTEA;
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS file_name TEXT;
    ''')
    cur.execute('''
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
    ''')

    # 3. Фиксируем изменения
    # =======================

    conn.commit()
    cur.close()
    conn.close()

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
        cur.execute('SELECT id, password, role FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and user[1] == password:
            session['user_id'] = user[0]
            session['role'] = user[2]  # Сохраняем роль
            return redirect(url_for('index'))
        flash("Неверный логин или пароль.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
    user_role = cur.fetchone()[0]
    cur.close()
    conn.close()

    if user_role != 'admin':
        flash("Только администратор может создавать пользователей.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'executor')
        manager_id = request.form.get('manager_id') or None

        if not username or not password:
            flash("Заполните все поля.")
            return redirect(url_for('register'))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('''
                INSERT INTO users (username, password, role, manager_id)
                VALUES (%s, %s, %s, %s)
            ''', (username, password, role, manager_id if role == 'executor' else None))
            conn.commit()
            flash(f"Пользователь {username} создан!")
        except psycopg2.IntegrityError:
            flash("Имя занято.")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('index'))

    # Получаем всех менеджеров для выбора
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE role = 'manager'")
    managers = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('register.html', managers=managers)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        project_id = request.form.get('project_id') or None
        assigned_to = request.form.get('assigned_to') or None
        due_date = request.form.get('due_date') or None
        description = request.form.get('description', '')
        file_data = None
        file_name = None

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and allowed_file(file.filename):
                file_data = file.read()
                file_name = secure_filename(file.filename)

        if title:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO tasks (title, description, due_date, created_by, assigned_to, project_id, file_data, file_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (title, description, due_date, session['user_id'], assigned_to, project_id, file_data, file_name))
            task_id = cur.fetchone()[0]

            # Логируем создание
            cur.execute('''
                INSERT INTO task_history (task_id, user_id, action, details)
                VALUES (%s, %s, 'created', 'Создана задача')
            ''', (task_id, session['user_id']))

            # Уведомление исполнителю
            if assigned_to:
                cur.execute('''
                    INSERT INTO notifications (user_id, message, link)
                    VALUES (%s, %s, %s)
                ''', (assigned_to, f"Вам назначена задача: {title}", f"/task/{task_id}"))

            conn.commit()
            cur.close()
            conn.close()
        return redirect(url_for('index'))

    # Получаем задачи (с фильтрацией)
    conn = get_db_connection()
    cur = conn.cursor()

    # Если исполнитель — видит только назначенные ему задачи
    # Если менеджер/админ — видит свои и назначенные
    if session['role'] == 'executor':
        cur.execute('''
            SELECT id, title, status, priority, due_date, file_name FROM tasks 
            WHERE assigned_to = %s ORDER BY due_date
        ''', (session['user_id'],))
    else:
        cur.execute('''
            SELECT id, title, status, priority, due_date, file_name FROM tasks 
            WHERE created_by = %s OR assigned_to = %s ORDER BY due_date
        ''', (session['user_id'], session['user_id']))

    tasks = cur.fetchall()
    cur.close()
    conn.close()

    # Получаем проекты и команду для формы
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects WHERE manager_id = %s OR created_by = %s", (session['user_id'], session['user_id']))
    projects = cur.fetchall()

    if session['role'] == 'manager':
        cur.execute("SELECT id, username FROM users WHERE manager_id = %s", (session['user_id'],))
    else:
        cur.execute("SELECT id, username FROM users WHERE role = 'executor'")
    team = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('index.html', tasks=tasks, projects=projects, team=team)

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

@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
def task_detail(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content'].strip()
        if content:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO comments (task_id, user_id, content)
                VALUES (%s, %s, %s)
            ''', (task_id, session['user_id'], content))
            conn.commit()
            cur.close()
            conn.close()
        return redirect(url_for('task_detail', task_id=task_id))

    # Получаем задачу и комментарии
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
    task = cur.fetchone()
    cur.execute('''
        SELECT c.content, u.username, c.created_at FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = %s ORDER BY c.created_at
    ''', (task_id,))
    comments = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('task_detail.html', task=task, comments=comments)

@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
    role = cur.fetchone()[0]

    if role not in ['manager', 'admin']:
        flash("Доступ запрещён.")
        return redirect(url_for('index'))

    # Статистика по команде
    cur.execute('''
        SELECT 
            u.username,
            COUNT(t.id) FILTER (WHERE t.status = 'new') as new,
            COUNT(t.id) FILTER (WHERE t.status = 'in_progress') as in_progress,
            COUNT(t.id) FILTER (WHERE t.status = 'done') as done
        FROM users u
        LEFT JOIN tasks t ON u.id = t.assigned_to
        WHERE u.manager_id = %s
        GROUP BY u.id
    ''', (session['user_id'],))
    team_stats = cur.fetchall()

    conn.close()
    return render_template('stats.html', stats=team_stats)

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT message, link, created_at, is_read FROM notifications
        WHERE user_id = %s ORDER BY created_at DESC
    ''', (session['user_id'],))
    notifs = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('notifications.html', notifications=notifs)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)