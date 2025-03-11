from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = "lowongan.db"

# Fungsi koneksi database
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Agar hasil query bisa diakses seperti dictionary
    return conn

# Inisialisasi database
def create_table():
    conn = get_db()
    cur = conn.cursor()
    # Tabel lowongan kerja
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lowongan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            gaji TEXT,
            company_address TEXT,
            syarat TEXT,
            logo TEXT,
            name TEXT,
            kategori TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    # Tabel pengguna
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')

    # Tabel untuk menyimpan Like
    cur.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id) REFERENCES lowongan(id),
            UNIQUE(user_id, job_id)  -- Hindari user yang sama like berkali-kali
        )
    ''')

    # Tabel untuk menyimpan Komentar
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id) REFERENCES lowongan(id)
        )
    ''')

    conn.commit()
    conn.close()

# Tambah admin jika belum ada
def create_admin():
    conn = get_db()
    cur = conn.cursor()

    email = "admin@mail.com"
    hashed_password = generate_password_hash("admin123")

    try:
        cur.execute("INSERT INTO users (first_name, last_name, email, password, role) VALUES (?, ?, ?, ?, 'admin')",
                    ("Admin", "User", email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Admin sudah ada

    conn.close()

# Panggil fungsi inisialisasi database saat server dimulai
create_table()
create_admin()

# Fungsi CRUD untuk lowongan kerja
def add_lowongan(title, description, gaji, company_address, syarat, logo_filename, name, kategori):
    conn = get_db()
    cur = conn.cursor()

    print(f"Menambahkan: {title}, {description}, {gaji}, {company_address}, {syarat}, {logo_filename}, {name}, {kategori}")  # Debugging

    cur.execute("INSERT INTO lowongan (title, description, gaji, company_address, syarat, logo, name, kategori, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                (title, description, gaji, company_address, syarat, logo_filename, name, kategori))
    conn.commit()


def get_pending_lowongan():
    conn = get_db()
    jobs = conn.execute("SELECT * FROM lowongan WHERE status = 'pending'").fetchall()
    conn.close()
    return jobs


def get_approved_lowongan():
    conn = get_db()
    jobs = conn.execute("SELECT * FROM lowongan WHERE status = 'approved'").fetchall()

    categorized_jobs = {}

    for job in jobs:
        job_id = job["id"]
        like_count = conn.execute("SELECT COUNT(*) FROM likes WHERE job_id = ?", (job_id,)).fetchone()[0]

        user_liked = False
        if "user_id" in session:
            user_id = session["user_id"]
            user_liked = conn.execute("SELECT 1 FROM likes WHERE user_id = ? AND job_id = ?",
                                      (user_id, job_id)).fetchone() is not None

        job_dict = dict(job)
        job_dict["like_count"] = like_count
        job_dict["liked"] = user_liked

        kategori = job["kategori"]
        if kategori not in categorized_jobs:
            categorized_jobs[kategori] = []
        categorized_jobs[kategori].append(job_dict)

    conn.close()
    return categorized_jobs


def update_lowongan_status(lowongan_id, status):
    conn = get_db()
    conn.execute("UPDATE lowongan SET status = ? WHERE id = ?", (status, lowongan_id))
    conn.commit()
    conn.close()

def delete_lowongan(lowongan_id):
    conn = get_db()
    conn.execute("DELETE FROM lowongan WHERE id = ?", (lowongan_id,))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('welcome.html')
@app.route('/home')
def home_page():
    conn = get_db()
    jobs = conn.execute("SELECT * FROM lowongan WHERE status = 'approved'").fetchall()

    categorized_jobs = {}  # Dictionary untuk menyimpan lowongan berdasarkan kategori
    user_id = session.get('user_id')

    for job in jobs:
        job_id = job["id"]
        like_count = conn.execute("SELECT COUNT(*) FROM likes WHERE job_id = ?", (job_id,)).fetchone()[0]

        user_liked = False
        if user_id:
            user_liked = conn.execute("SELECT 1 FROM likes WHERE user_id = ? AND job_id = ?",
                                      (user_id, job_id)).fetchone() is not None

        job_dict = dict(job)
        job_dict["like_count"] = like_count
        job_dict["user_liked"] = user_liked

        kategori = job["kategori"]
        if kategori not in categorized_jobs:
            categorized_jobs[kategori] = []

        categorized_jobs[kategori].append(job_dict)

    conn.close()
    return render_template('home.html', jobs=categorized_jobs)

@app.route('/lowongan')
def lowongan():
    approved_jobs_dict = get_approved_lowongan()

    # Ubah dictionary ke list, tapi tetap simpan kategori di dalamnya
    approved_jobs_list = []
    for kategori, job_list in approved_jobs_dict.items():
        for job in job_list:
            job["kategori"] = kategori  # Tambahkan kategori ke dalam data lowongan
            approved_jobs_list.append(job)

    return render_template('lowongan.html', jobs=approved_jobs_list)


@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        gaji = request.form.get('gaji', 'Tidak disebutkan')  # Ganti salary jadi gaji
        company_address = request.form['company_address']
        syarat = request.form['syarat']
        name = request.form['name']
        kategori = request.form['kategori']

        # Ambil file logo
        logo = request.files.get('logo')
        logo_filename = None

        if logo and logo.filename:  # Periksa apakah ada file yang diunggah
            logo_filename = secure_filename(logo.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
            logo.save(logo_path)  # Simpan file logo

        # Simpan lowongan ke database
        add_lowongan(title, description, gaji, company_address, syarat, logo_filename, name, kategori)

        return redirect(url_for('home_page'))

    return render_template('add_item.html')

@app.route('/confirm_lowongan', methods=['GET', 'POST'])
def confirm_lowongan():
    if session.get('role') != 'admin':
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        lowongan_id = request.form['lowongan_id']
        action = request.form['action']

        if action == 'approve':
            update_lowongan_status(lowongan_id, 'approved')
        elif action == 'reject':
            update_lowongan_status(lowongan_id, 'rejected')
        elif action == 'delete':
            delete_lowongan(lowongan_id)

    pending_jobs = get_pending_lowongan()
    return render_template('confirm_lowongan.html', jobs=pending_jobs)

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/job/<int:job_id>')
def job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM lowongan WHERE id = ?", (job_id,)).fetchone()

    if not job:
        return "Lowongan tidak ditemukan", 404

    # Ambil komentar terkait lowongan
    comments = conn.execute("""
        SELECT comments.comment, users.first_name FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.job_id = ?
    """, (job_id,)).fetchall()

    # Ambil jumlah like
    like_count = conn.execute("SELECT COUNT(*) FROM likes WHERE job_id = ?", (job_id,)).fetchone()[0]

    # Cek apakah user yang sedang login sudah menyukai lowongan ini
    user_liked = False
    if 'user_id' in session:
        user_id = session['user_id']
        user_liked = conn.execute("SELECT 1 FROM likes WHERE user_id = ? AND job_id = ?",
                                  (user_id, job_id)).fetchone() is not None

    conn.close()

    return render_template('job_detail.html', job=job, comments=comments, like_count=like_count, user_liked=user_liked)

@app.route('/delete_lowongan', methods=['POST'])
def delete_lowongan_route():
    if session.get('role') != 'admin':
        return redirect(url_for('home_page'))

    lowongan_id = request.form.get('lowongan_id')
    if lowongan_id:
        delete_lowongan(lowongan_id)

    return redirect(url_for('lowongan'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session['user_id'] = user["id"]
            session['role'] = user["role"]
            return redirect(url_for('home_page'))
        else:
            return render_template('login.html', error="Email atau Password salah!")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('register.html', error="Password tidak cocok!")

        hashed_password = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (first_name, last_name, email, password, role) VALUES (?, ?, ?, ?, 'user')",
                         (first_name, last_name, email, hashed_password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Email sudah digunakan!")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/category/<category>')
def category_jobs(category):
    conn = get_db()
    jobs = conn.execute("SELECT * FROM lowongan WHERE status = 'approved' AND kategori = ?", (category,)).fetchall()
    conn.close()

    return render_template('category.html', category=category, jobs=jobs)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/like/<int:job_id>', methods=['POST'])
def like_job(job_id):
    if 'user_id' not in session:
        return jsonify({"error": "Anda harus login"}), 401

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()

    # Cek apakah user sudah like sebelumnya
    user_liked = cur.execute("SELECT 1 FROM likes WHERE user_id = ? AND job_id = ?", (user_id, job_id)).fetchone()

    if user_liked:
        # Jika sudah like, maka hapus like (unlike)
        cur.execute("DELETE FROM likes WHERE user_id = ? AND job_id = ?", (user_id, job_id))
        action = "unliked"
    else:
        # Jika belum like, maka tambahkan like
        cur.execute("INSERT INTO likes (user_id, job_id) VALUES (?, ?)", (user_id, job_id))
        action = "liked"

    conn.commit()

    # Hitung jumlah like terbaru
    like_count = cur.execute("SELECT COUNT(*) FROM likes WHERE job_id = ?", (job_id,)).fetchone()[0]
    conn.close()

    return jsonify({"status": action, "like_count": like_count})



# Endpoint untuk Komentar
@app.route('/comment', methods=['POST'])
def add_comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    job_id = request.form.get('job_id')
    comment = request.form.get('comment')

    if not comment.strip():
        return redirect(url_for('job_detail', job_id=job_id))  # Hindari komentar kosong

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (user_id, job_id, comment) VALUES (?, ?, ?)", (user_id, job_id, comment))
    conn.commit()
    conn.close()

    return redirect(url_for('job_detail', job_id=job_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
