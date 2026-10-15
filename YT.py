
import os
import sys
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    raise SystemExit(
        "yt-dlp is missing. Run: py -m pip install -U yt-dlp"
    )


# ---------------- Configuration ----------------

APP_TITLE = "YouTube Downloader"
BG = "#10141F"
PANEL = "#191F2E"
INPUT_BG = "#242C3D"
TEXT = "#F3F5FA"
MUTED = "#A8B2C5"
ACCENT = "#6C63FF"
SUCCESS = "#42D392"
ERROR = "#FF7272"


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("760x650")
        self.root.minsize(650, 590)
        self.root.configure(bg=BG)

        self.events = queue.Queue()
        self.downloading = False
        self.download_folder = os.path.join(
            os.path.expanduser("~"), "Downloads"
        )

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Video (MP4)")
        self.quality_var = tk.StringVar(value="1080p")
        self.playlist_var = tk.BooleanVar(value=False)
        self.folder_var = tk.StringVar(value=self.download_folder)
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Ready to download")
        self.detail_var = tk.StringVar(value="Paste a video or playlist URL.")

        self.setup_styles()
        self.build_ui()

        self.root.after(100, self.process_events)

    # ---------------- UI ----------------

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TCombobox",
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            arrowcolor=TEXT,
            padding=7,
        )

        style.map(
            "TCombobox",
            fieldbackground=[("readonly", INPUT_BG)],
            foreground=[("readonly", TEXT)],
        )

        style.configure(
            "Download.Horizontal.TProgressbar",
            troughcolor=INPUT_BG,
            background=ACCENT,
            bordercolor=INPUT_BG,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )

    def build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=30, pady=(24, 18))

        tk.Label(
            header,
            text="▶  YouTube Downloader",
            font=("Segoe UI", 23, "bold"),
            bg=BG,
            fg=TEXT,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Download videos and audio with a simple desktop interface",
            font=("Segoe UI", 10),
            bg=BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(5, 0))

        panel = tk.Frame(self.root, bg=PANEL)
        panel.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        content = tk.Frame(panel, bg=PANEL)
        content.pack(fill="both", expand=True, padx=24, pady=22)

        self.add_label(content, "YouTube video or playlist URL")

        url_row = tk.Frame(content, bg=PANEL)
        url_row.pack(fill="x", pady=(7, 18))

        self.url_entry = tk.Entry(
            url_row,
            textvariable=self.url_var,
            font=("Segoe UI", 11),
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
        )
        self.url_entry.pack(
            side="left", fill="x", expand=True, ipady=12, padx=(0, 8)
        )

        self.make_button(
            url_row, "Paste", self.paste_url, small=True
        ).pack(side="right")

        options = tk.Frame(content, bg=PANEL)
        options.pack(fill="x", pady=(0, 16))

        left = tk.Frame(options, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))

        right = tk.Frame(options, bg=PANEL)
        right.pack(side="left", fill="x", expand=True)

        self.add_label(left, "Download format")
        self.mode_combo = ttk.Combobox(
            left,
            textvariable=self.mode_var,
            values=["Video (MP4)", "Audio (MP3)"],
            state="readonly",
        )
        self.mode_combo.pack(fill="x", pady=(7, 0))
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.add_label(right, "Video quality")
        self.quality_combo = ttk.Combobox(
            right,
            textvariable=self.quality_var,
            values=["Best available", "1080p", "720p", "480p", "360p"],
            state="readonly",
        )
        self.quality_combo.pack(fill="x", pady=(7, 0))

        tk.Checkbutton(
            content,
            text="Download the entire playlist (if applicable)",
            variable=self.playlist_var,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=INPUT_BG,
            font=("Segoe UI", 10),
            cursor="hand2",
        ).pack(anchor="w", pady=(0, 17))

        self.add_label(content, "Save location")

        folder_row = tk.Frame(content, bg=PANEL)
        folder_row.pack(fill="x", pady=(7, 18))

        self.folder_entry = tk.Entry(
            folder_row,
            textvariable=self.folder_var,
            font=("Segoe UI", 10),
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            state="readonly",
            readonlybackground=INPUT_BG,
        )
        self.folder_entry.pack(
            side="left", fill="x", expand=True, ipady=10, padx=(0, 8)
        )

        self.make_button(
            folder_row, "Browse", self.choose_folder, small=True
        ).pack(side="right")

        self.download_button = self.make_button(
            content, "↓   Start Download", self.start_download
        )
        self.download_button.pack(fill="x", ipady=5, pady=(0, 20))

        tk.Label(
            content,
            textvariable=self.status_var,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        self.progress = ttk.Progressbar(
            content,
            variable=self.progress_var,
            maximum=100,
            style="Download.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(9, 7))

        tk.Label(
            content,
            textvariable=self.detail_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=620,
            justify="left",
        ).pack(anchor="w")

        footer = tk.Label(
            self.root,
            text="Use only for content you own or are authorized to download.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        footer.pack(pady=(0, 13))

    def add_label(self, parent, text):
        tk.Label(
            parent,
            text=text,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

    def make_button(self, parent, text, command, small=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT,
            fg="white",
            activebackground="#5750D8",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=15 if small else 12,
            pady=8,
        )

    # ---------------- Actions ----------------

    def paste_url(self):
        try:
            clipboard = self.root.clipboard_get()
            self.url_var.set(clipboard.strip())
        except tk.TclError:
            self.status_var.set("Clipboard is empty.")

    def choose_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.folder_var.get()
        )
        if folder:
            self.folder_var.set(folder)
            self.download_folder = folder

    def on_mode_change(self, _event=None):
        if self.mode_var.get() == "Audio (MP3)":
            self.quality_combo.configure(state="disabled")
        else:
            self.quality_combo.configure(state="readonly")

    def start_download(self):
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()

        if not url:
            messagebox.showwarning(
                "Missing URL", "Please paste a YouTube URL first."
            )
            return

        if not url.startswith(("https://", "http://")):
            messagebox.showwarning(
                "Invalid URL", "Please enter a valid HTTP or HTTPS URL."
            )
            return

        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                "Invalid folder", "Please select an existing save folder."
            )
            return

        if self.downloading:
            return

        self.downloading = True
        self.download_button.configure(
            state="disabled", text="Downloading..."
        )
        self.progress_var.set(0)
        self.status_var.set("Preparing download...")
        self.detail_var.set("Connecting to YouTube...")

        settings = {
            "url": url,
            "folder": folder,
            "mode": self.mode_var.get(),
            "quality": self.quality_var.get(),
            "playlist": self.playlist_var.get(),
        }

        threading.Thread(
            target=self.download_worker,
            args=(settings,),
            daemon=True,
        ).start()

    # ---------------- Download engine ----------------

    def download_worker(self, settings):
        folder = settings["folder"]
        is_audio = settings["mode"] == "Audio (MP3)"
        allow_playlist = settings["playlist"]

        options = {
            "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
            "noplaylist": not allow_playlist,
            "ignoreerrors": False,
            "retries": 3,
            "continuedl": True,
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if is_audio:
            options.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            quality = settings["quality"]

            if quality == "Best available":
                options["format"] = "bestvideo+bestaudio/best"
            else:
                height = int(quality.replace("p", ""))
                options["format"] = (
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]"
                )

            options["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([settings["url"]])

            self.events.put((
                "done",
                "Download finished. Check your selected folder."
            ))

        except Exception as exc:
            self.events.put(("error", str(exc)))

    def progress_hook(self, data):
        state = data.get("status")

        if state == "downloading":
            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
                or 0
            )
            downloaded = data.get("downloaded_bytes", 0)

            percent = downloaded * 100 / total if total else 0
            speed = data.get("_speed_str", "calculating speed")
            eta = data.get("_eta_str", "calculating time")
            filename = os.path.basename(data.get("filename", ""))
            filename = filename[:65]

            self.events.put((
                "progress",
                percent,
                f"{filename} | {speed} | ETA: {eta}",
            ))

        elif state == "finished":
            self.events.put((
                "progress",
                100,
                "Download received; processing or merging files...",
            ))

    # ---------------- Thread-safe UI updates ----------------

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, percent, detail = event
                    self.progress_var.set(percent)
                    self.status_var.set(
                        "Downloading..." if percent < 100
                        else "Processing file..."
                    )
                    self.detail_var.set(detail)

                elif kind == "done":
                    self.downloading = False
                    self.download_button.configure(
                        state="normal", text="↓   Start Download"
                    )
                    self.progress_var.set(100)
                    self.status_var.set("✓  Completed successfully")
                    self.detail_var.set(event[1])
                    messagebox.showinfo("Success", event[1])

                elif kind == "error":
                    self.downloading = False
                    self.download_button.configure(
                        state="normal", text="↓   Start Download"
                    )
                    self.status_var.set("Download failed")
                    self.detail_var.set(event[1][:350])
                    messagebox.showerror(
                        "Download error",
                        event[1][:1500]
                        + "\n\nCheck the URL, your connection, "
                        "yt-dlp, and FFmpeg installation."
                    )

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
