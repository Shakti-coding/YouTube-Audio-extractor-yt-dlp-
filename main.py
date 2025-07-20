from flask import Flask, render_template_string, request, redirect, send_file, session, url_for, jsonify
import subprocess
import os
import json
from threading import Thread
from werkzeug.utils import secure_filename
import zipfile

app = Flask(__name__)
app.secret_key = 'securekey123'

# Directories
WORK_DIR = os.path.expanduser("~/ncert_audio_web")
AUDIO_DIR = os.path.join(WORK_DIR, "audio")
TMP_DIR = os.path.join(WORK_DIR, "temp")
UPLOAD_DIR = os.path.join(WORK_DIR, "uploads")
JSON_CACHE = os.path.join(WORK_DIR, "videos.json")
LOG_FILE = os.path.join(WORK_DIR, "log.txt")

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Login credentials
USERS = {'admin': 'password123'}

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{msg}\n")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if USERS.get(u) == p:
            session['user'] = u
            return redirect('/')
        return "Invalid credentials", 401
    return '''<form method="post">
                <input name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
              </form>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect('/login')

    channel_url = request.form.get("channel_url") or "https://www.youtube.com/@ncert_audio_books"
    videos = []
    audio_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")])

    if request.method == 'POST':
        if 'search' in request.form:
            subprocess.run(f"yt-dlp --flat-playlist --dump-json {channel_url} > {JSON_CACHE}", shell=True)
        elif 'extract' in request.form:
            bot_token = request.form["bot_token"]
            chat_id = request.form["chat_id"]
            selected_ids = request.form.getlist("videos")
            Thread(target=download_and_forward, args=(selected_ids, bot_token, chat_id)).start()
        elif 'upload_bot' in request.form:
            file = request.files['uploadfile']
            bot_token = request.form["bot_token"]
            chat_id = request.form["chat_id"]
            filename = secure_filename(file.filename)
            path = os.path.join(TMP_DIR, filename)
            file.save(path)
            Thread(target=send_uploaded_file_to_bot, args=(path, bot_token, chat_id)).start()

    if os.path.exists(JSON_CACHE):
        with open(JSON_CACHE, 'r') as f:
            videos = [json.loads(line.strip()) for line in f if 'title' in line]

    with open(LOG_FILE, 'r') as f:
        logs = f.read()

    return render_template_string(TEMPLATE, videos=videos, audio_files=audio_files, log=logs, channel_url=channel_url)

@app.route('/log')
def get_log():
    with open(LOG_FILE, 'r') as f:
        return f.read()

@app.route('/videos')
def get_videos():
    if os.path.exists(JSON_CACHE):
        with open(JSON_CACHE, 'r') as f:
            videos = [json.loads(line.strip()) for line in f if 'title' in line]
        return jsonify(videos)
    return jsonify([])

@app.route('/play/<filename>')
def play_audio(filename):
    return send_file(os.path.join(AUDIO_DIR, filename))

@app.route('/download/<filename>')
def download_audio(filename):
    return send_file(os.path.join(AUDIO_DIR, filename), as_attachment=True)

@app.route('/download_zip', methods=['POST'])
def download_zip():
    selected = request.form.getlist("files")
    zip_path = os.path.join(WORK_DIR, "audios.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in selected:
            zipf.write(os.path.join(AUDIO_DIR, file), arcname=file)
    return send_file(zip_path, as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)
    Thread(target=extract_audio_from_file, args=(filepath,)).start()
    return redirect('/')

def extract_audio_from_file(filepath):
    title = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(AUDIO_DIR, f"{title}.mp3")
    log(f"🎞️ Extracting from file: {filepath}")
    subprocess.run(f"ffmpeg -i '{filepath}' -q:a 0 -map a '{out_path}'", shell=True)
    os.remove(filepath)
    log(f"✅ Extracted and saved: {out_path}")

def download_and_forward(video_ids, bot_token, chat_id):
    log("📥 Starting download and forward...")
    for vid in video_ids:
        url = f"https://www.youtube.com/watch?v={vid}"
        log(f"🔗 Downloading: {url}")
        subprocess.run(f"yt-dlp -x --audio-format mp3 --embed-thumbnail --add-metadata -o '{TMP_DIR}/%(title)s.%(ext)s' {url}", shell=True)

    for file in os.listdir(TMP_DIR):
        if file.endswith(".mp3"):
            path = os.path.join(TMP_DIR, file)
            log(f"📤 Forwarding: {file}")
            subprocess.run([
                "curl", "-s", "-X", "POST",
                f"https://api.telegram.org/bot{bot_token}/sendAudio",
                "-F", f"chat_id={chat_id}",
                "-F", f"audio=@{path}",
                "-F", f"title={file}",
                "-F", f"performer=NCERT Audio Book"
            ])
            os.remove(path)
            log(f"✅ Done and deleted local: {file}")
    log("🎉 All done.")

def send_uploaded_file_to_bot(path, bot_token, chat_id):
    filename = os.path.basename(path)
    log(f"🚀 Uploading file to bot: {filename}")
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        "-F", f"chat_id={chat_id}",
        "-F", f"document=@{path}",
        "-F", f"caption=📤 Uploaded File: {filename}"
    ])
    os.remove(path)
    log(f"✅ Uploaded and removed: {filename}")

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <title>NCERT Audio Extractor</title>
  <style>
    body { font-family: sans-serif; background: #f8f8f8; padding: 10px; }
    .video-list { max-height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; background: #fff; }
    .video { display: flex; gap: 10px; margin: 5px 0; padding: 5px; border: 1px solid #ddd; background: #fefefe; }
    .thumb { width: 100px; }
    audio { width: 100%; margin-top: 5px; }
    textarea { width: 100%; height: 150px; }
    .top-bar { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
  </style>
</head>
<body>
  <h1>🎧 NCERT Audio Extractor</h1>
  <div id="statusBar" style="margin:10px 0; font-weight:bold; color:green;"></div>
  <progress id="progressBar" style="width:100%;" value="0" max="100" hidden></progress>

  <form method="post" enctype="multipart/form-data">
    <div class="top-bar">
      <input name="channel_url" value="{{ channel_url }}" placeholder="YouTube channel link" style="flex:2">
      <input name="bot_token" placeholder="Telegram Bot Token" style="flex:1">
      <input name="chat_id" placeholder="Chat ID" style="flex:1">
      <button name="search">🔍 Search</button>
      <button name="extract">🎵 Extract</button>
    </div>
    <label><input type="checkbox" onclick="selectAll(this)"> Select All</label>
    <div class="video-list" id="videoList">
      {% for v in videos %}
        <div class="video" data-title="{{ v['title'] | lower }}">
          <input type="checkbox" name="videos" value="{{ v['id'] }}">
          <img class="thumb" src="https://i.ytimg.com/vi/{{ v['id'] }}/hqdefault.jpg">
          <div style="flex:1">
            <b>{{ v['title'] }}</b><br>
            <a target="_blank" href="https://www.youtube.com/watch?v={{ v['id'] }}">▶️ Play</a>
          </div>
        </div>
      {% endfor %}
    </div>

    <h2>🎶 Your Extracted Audio Files</h2>
    {% for f in audio_files %}
      <div>
        <b>{{ f }}</b><br>
        <audio controls src="/play/{{ f }}"></audio><br>
        <a href="/download/{{ f }}">⬇️ Download</a>
      </div>
    {% endfor %}
    <form method="POST" action="/download_zip">
      {% for f in audio_files %}
        <input type="checkbox" name="files" value="{{ f }}"> {{ f }}<br>
      {% endfor %}
      <button type="submit">⬇️ Download ZIP</button>
    </form>

    <h2>📤 Upload Local Video and Extract Audio</h2>
    <form method="POST" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file" accept="video/*" required>
      <button type="submit">Upload and Extract</button>
    </form>

    <h2>📤 Upload Any File to Telegram Bot</h2>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="uploadfile" required>
      <input type="text" name="bot_token" placeholder="Bot Token" required>
      <input type="text" name="chat_id" placeholder="Chat ID" required>
      <button type="submit" name="upload_bot">📤 Send File to Bot</button>
    </form>

    <h2>📋 Log Output</h2>
    <pre id="logbox">{{ log }}</pre>
  </form>

  <script>
    function selectAll(source) {
      const checkboxes = document.querySelectorAll('input[name="videos"]');
      checkboxes.forEach(c => c.checked = source.checked);
    }

    setInterval(() => {
      fetch('/log').then(r => r.text()).then(txt => {
        document.getElementById('logbox').innerText = txt;
        if (txt.includes("🎉 All done.") || txt.includes("✅ Uploaded and removed")) {
          document.getElementById('progressBar').hidden = true;
          document.getElementById('statusBar').innerText = '✅ Task Finished';
        }
      });
    }, 4000);

    document.querySelector("button[name='search']").addEventListener("click", () => {
      document.getElementById("statusBar").innerText = "⏳ Searching videos...";
      document.getElementById("progressBar").hidden = false;
      document.getElementById("progressBar").value = 10;
      setTimeout(() => {
        fetch('/videos').then(res => res.json()).then(data => {
          let container = document.getElementById("videoList");
          container.innerHTML = "";
          data.forEach(v => {
            container.innerHTML += `
              <div class="video" data-title="${v.title.toLowerCase()}">
                <input type="checkbox" name="videos" value="${v.id}">
                <img class="thumb" src="https://i.ytimg.com/vi/${v.id}/hqdefault.jpg">
                <div style="flex:1">
                  <b>${v.title}</b><br>
                  <a target="_blank" href="https://www.youtube.com/watch?v=${v.id}">▶️ Play</a>
                </div>
              </div>`;
          });
          document.getElementById("statusBar").innerText = "✅ Videos Loaded";
          document.getElementById("progressBar").value = 100;
        });
      }, 4000);
    });

    const uploadForms = document.querySelectorAll("form");
    uploadForms.forEach(form => {
      form.addEventListener("submit", () => {
        document.getElementById('statusBar').innerText = '⏳ Working...';
        document.getElementById('progressBar').hidden = false;
        document.getElementById('progressBar').value = 50;
      });
    });
  </script>
</body>
</html>
'''

if __name__ == '__main__':
    open(LOG_FILE, 'w').close()
    app.run(host='0.0.0.0', port=8000)
