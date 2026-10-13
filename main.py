import os
import socket
import threading
import customtkinter as ctk
from tkinter import filedialog
from flask import Flask, request, render_template_string, send_from_directory, jsonify
import qrcode
from PIL import Image

LANG = {
    'en': {
        'window_title': 'Easy-Transfer',
        'web_conn': 'Web Connection',
        'curr_dir': 'Current Directory:\n',
        'change_folder': 'Change Folder',
        'history': 'History',
        'web_title': 'Local Transfer',
        'send_pc': 'Send to PC',
        'sel_files': 'Select Files',
        'waiting': 'Waiting for files...',
        'dl_pc': 'Download from PC',
        'empty_folder': 'The folder is empty.',
        'files_queue': 'file(s) in queue...',
        'all_done': 'All transfers completed.',
        'sending': 'Sending: ',
        'remaining': ' remaining)'
    },
    'es': {
        'window_title': 'Easy-Transfer',
        'web_conn': 'Conexión Web',
        'curr_dir': 'Directorio Actual:\n',
        'change_folder': 'Cambiar Carpeta',
        'history': 'Historial',
        'web_title': 'Transferencia Local',
        'send_pc': 'Enviar a la PC',
        'sel_files': 'Seleccionar Archivos',
        'waiting': 'Esperando archivos...',
        'dl_pc': 'Descargar desde la PC',
        'empty_folder': 'La carpeta está vacía.',
        'files_queue': 'archivo(s) en cola...',
        'all_done': 'Todas las transferencias completadas.',
        'sending': 'Enviando: ',
        'remaining': ' restantes)'
    }
}
CURRENT_LANG = 'en'  # Inglés por defecto

# flask config
app = Flask(__name__)
SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads')
transfers = {}
upload_counter = 0

# web
HTML_TEMPLATE = """
<!doctype html>
<html lang="{{ current_lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ texts.web_title }}</title>
  <style>
    body { font-family: "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #121212; color: #e0e0e0; }
    .lang-switch { text-align: right; margin-bottom: 15px; }
    .lang-switch a { display: inline-block; padding: 5px 10px; color: #4da6ff; text-decoration: none; font-weight: bold; border-radius: 4px; }
    .lang-switch a:hover { background: #2d2d2d; }
    .card { background: #1e1e1e; padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid #2d2d2d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    h2 { margin-top: 0; font-size: 18px; font-weight: 600; color: #ffffff; border-bottom: 1px solid #2d2d2d; padding-bottom: 10px; }
    .file-input-wrapper { position: relative; overflow: hidden; display: block; width: 100%; margin-top: 20px; }
    .btn { background: #1f6aa5; color: white; border: none; padding: 14px; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: 500; transition: background 0.2s; }
    .btn:hover { background: #144870; }
    input[type=file] { font-size: 100px; position: absolute; left: 0; top: 0; opacity: 0; cursor: pointer; height: 100%; width: 100%; }
    .status-text { font-size: 14px; color: #888; margin-top: 15px; text-align: center; }
    .file-list { margin-top: 15px; }
    a.file-link { text-decoration: none; color: #4da6ff; display: block; padding: 12px 0; border-bottom: 1px solid #2d2d2d; transition: color 0.2s; }
    a.file-link:hover { color: #80c2ff; }
    a.file-link:last-child { border-bottom: none; }
  </style>
</head>
<body>
  <div class="lang-switch">
      <a href="/?lang=en">EN</a> | <a href="/?lang=es">ES</a>
  </div>

  <div class="card">
    <h2>{{ texts.send_pc }}</h2>
    <div class="file-input-wrapper">
      <button class="btn">{{ texts.sel_files }}</button>
      <input type="file" id="fileInput" multiple>
    </div>
    <div id="status" class="status-text">{{ texts.waiting }}</div>
  </div>
  
  <div class="card">
    <h2>{{ texts.dl_pc }}</h2>
    <div class="file-list">
      {% for f in files %}
        <a href="/download/{{ f }}" class="file-link" download>{{ f }}</a>
      {% else %}
        <p style="color: #666; font-size: 14px; text-align: center;">{{ texts.empty_folder }}</p>
      {% endfor %}
    </div>
  </div>

  <script>
    const i18n = {
        queue: "{{ texts.files_queue }}",
        done: "{{ texts.all_done }}",
        sending: "{{ texts.sending }}",
        remaining: "{{ texts.remaining }}"
    };

    const queue = [];
    let isUploading = false;
    const statusDiv = document.getElementById('status');

    document.getElementById('fileInput').addEventListener('change', (e) => {
        for (let f of e.target.files) queue.push(f);
        statusDiv.innerText = queue.length + " " + i18n.queue;
        processQueue();
    });

    async function processQueue() {
        if (isUploading || queue.length === 0) {
            if (queue.length === 0 && !isUploading) {
                statusDiv.innerText = i18n.done;
                setTimeout(() => location.reload(), 2000);
            }
            return;
        }
        
        isUploading = true;
        const file = queue.shift();
        statusDiv.innerText = i18n.sending + file.name + " (" + queue.length + i18n.remaining;
        
        try {
            let res = await fetch('/upload_init', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: file.name, size: file.size})
            });
            let data = await res.json();
            let uploadId = data.upload_id;

            const chunkSize = 1024 * 1024; 
            for (let start = 0; start < file.size; start += chunkSize) {
                let chunk = file.slice(start, start + chunkSize);
                await fetch('/upload_chunk/' + uploadId, { method: 'POST', body: chunk });
            }

            await fetch('/upload_finish/' + uploadId, { method: 'POST' });
        } catch (e) {
            console.error("Error subiendo " + file.name);
        }
        
        isUploading = false;
        processQueue();
    }
  </script>
</body>
</html>
"""

# rutas
@app.route('/')
def index():
    global CURRENT_LANG
    req_lang = request.args.get('lang')
    if req_lang in ['en', 'es']:
        CURRENT_LANG = req_lang
        
    try:
        files = [f for f in os.listdir(SHARED_FOLDER) if os.path.isfile(os.path.join(SHARED_FOLDER, f))]
    except:
        files = []
    return render_template_string(HTML_TEMPLATE, files=files, texts=LANG[CURRENT_LANG], current_lang=CURRENT_LANG)

@app.route('/upload_init', methods=['POST'])
def upload_init():
    global upload_counter
    data = request.json
    upload_id = str(upload_counter)
    upload_counter += 1
    
    filename = os.path.basename(data['filename'])
    if not filename: filename = "archivo_desconocido"
    
    filepath = os.path.join(SHARED_FOLDER, filename)
    with open(filepath, 'wb') as f:
        pass
        
    transfers[upload_id] = {
        'filename': filename,
        'filepath': filepath,
        'size': data['size'],
        'received': 0,
        'status': 'active'
    }
    return jsonify({"upload_id": upload_id})

@app.route('/upload_chunk/<upload_id>', methods=['POST'])
def upload_chunk(upload_id):
    if upload_id in transfers:
        chunk = request.data
        with open(transfers[upload_id]['filepath'], 'ab') as f:
            f.write(chunk)
        transfers[upload_id]['received'] += len(chunk)
    return "ok"

@app.route('/upload_finish/<upload_id>', methods=['POST'])
def upload_finish(upload_id):
    if upload_id in transfers:
        transfers[upload_id]['status'] = 'done'
    return "ok"

@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(SHARED_FOLDER, filename, as_attachment=True)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def start_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# interfaz 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        t = LANG[CURRENT_LANG]
        self.title(t['window_title'])
        self.geometry("750x500")
        self.minsize(600, 400)
        self.ui_widgets = {}
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # panel lateral
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=t['web_conn'], font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Generar QR
        ip = get_local_ip()
        self.url = f"http://{ip}:5000"
        qr = qrcode.QRCode(box_size=8, border=1)
        qr.add_data(self.url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="#2b2b2b").get_image()
        
        self.qr_image = ctk.CTkImage(light_image=img_qr, dark_image=img_qr, size=(160, 160))
        self.qr_label = ctk.CTkLabel(self.sidebar_frame, image=self.qr_image, text="")
        self.qr_label.grid(row=1, column=0, padx=20, pady=10)
        self.url_label = ctk.CTkLabel(self.sidebar_frame, text=self.url, text_color="#4da6ff", font=ctk.CTkFont(size=12))
        self.url_label.grid(row=2, column=0, padx=20, pady=0)
        
        # Información de Directorio
        self.lbl_folder = ctk.CTkLabel(self.sidebar_frame, text=f"{t['curr_dir']}{SHARED_FOLDER}", font=ctk.CTkFont(size=11), text_color="#aaaaaa", wraplength=180)
        self.lbl_folder.grid(row=3, column=0, padx=20, pady=(20, 5))
        self.btn_folder = ctk.CTkButton(self.sidebar_frame, text=t['change_folder'], command=self.change_folder)
        self.btn_folder.grid(row=4, column=0, padx=20, pady=10)
        
        # Selector de Idiomas
        self.lang_switch = ctk.CTkSegmentedButton(self.sidebar_frame, values=["EN", "ES"], command=self.change_language)
        self.lang_switch.grid(row=5, column=0, padx=20, pady=(10, 20))
        self.lang_switch.set("EN" if CURRENT_LANG == 'en' else "ES")
        
        # progresos
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.queue_label = ctk.CTkLabel(self.main_frame, text=t['history'], font=ctk.CTkFont(size=20, weight="bold"))
        self.queue_label.pack(anchor="w", pady=(0, 15))
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Iniciar servidor flask
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        self.after(50, self.poll_transfers)

    def change_language(self, choice):
        global CURRENT_LANG
        CURRENT_LANG = 'en' if choice == "EN" else 'es'
        t = LANG[CURRENT_LANG]
        
        self.title(t['window_title'])
        self.logo_label.configure(text=t['web_conn'])
        self.lbl_folder.configure(text=f"{t['curr_dir']}{SHARED_FOLDER}")
        self.btn_folder.configure(text=t['change_folder'])
        self.queue_label.configure(text=t['history'])

    def change_folder(self):
        global SHARED_FOLDER
        new_folder = filedialog.askdirectory(initialdir=SHARED_FOLDER)
        if new_folder:
            SHARED_FOLDER = new_folder
            t = LANG[CURRENT_LANG]
            self.lbl_folder.configure(text=f"{t['curr_dir']}{SHARED_FOLDER}")
            
    def open_file(self, filepath):
        try:
            os.startfile(filepath)
        except Exception as e:
            print(f"Error al abrir: {e}")

    def discard_transfer(self, uid):
        if uid in self.ui_widgets:
            self.ui_widgets[uid]["frame"].destroy()
            del self.ui_widgets[uid]
        if uid in transfers:
            del transfers[uid]

    def delete_file(self, uid, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error al eliminar: {e}")
        self.discard_transfer(uid)

    def poll_transfers(self):
        for uid, data in list(transfers.items()):
            if uid not in self.ui_widgets:
                frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#2b2b2b")
                frame.pack(fill="x", pady=5, padx=5)
                top_frame = ctk.CTkFrame(frame, fg_color="transparent")
                top_frame.pack(fill="x", padx=15, pady=(15, 5))
                lbl = ctk.CTkLabel(top_frame, text=data['filename'], font=ctk.CTkFont(size=14, weight="bold"), cursor="hand2")
                lbl.pack(side="left")
                lbl.bind("<Double-1>", lambda e, path=data['filepath']: self.open_file(path))
                btn_del = ctk.CTkButton(top_frame, text="X", width=24, height=24, font=ctk.CTkFont(size=11), 
                                        fg_color="#a83232", hover_color="#7a2222", 
                                        command=lambda u=uid, p=data['filepath']: self.delete_file(u, p))
                btn_del.pack(side="right", padx=(5, 0))
                btn_discard = ctk.CTkButton(top_frame, text="-", width=24, height=24, font=ctk.CTkFont(size=11), 
                                            fg_color="#555555", hover_color="#333333", 
                                            command=lambda u=uid: self.discard_transfer(u))
                btn_discard.pack(side="right")
                
                pb = ctk.CTkProgressBar(frame, progress_color="#700505")
                pb.set(0)
                pb.pack(fill="x", padx=15, pady=(0, 15))
                
                self.ui_widgets[uid] = {
                    "frame": frame,
                    "pb": pb,
                    "lbl": lbl,
                    "current_val": 0.0
                }
                
            widget = self.ui_widgets[uid]
            target = data['received'] / max(1, data['size'])
            
            # animaciones
            if widget["current_val"] < target:
                widget["current_val"] += 0.04
                if widget["current_val"] > target:
                    widget["current_val"] = target
                widget["pb"].set(widget["current_val"])
                
            if data['status'] == 'done' and widget["current_val"] >= 0.99:
                widget["pb"].configure(progress_color="#ed00ed")
                
        self.after(50, self.poll_transfers)

if __name__ == "__main__":
    app_gui = App()
    app_gui.mainloop()