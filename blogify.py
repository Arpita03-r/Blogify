"""
Blogify - A single-file Tkinter app with MySQL backend

Features:
- Authentication (User login/registration, Admin login)
- User dashboard with scrollable feed: create/edit/delete posts, like, comment, follow
- Profile page: stats using MySQL functions, edit bio
- Notifications: list and mark as read (populated by DB triggers)
- Admin dashboard: view users/posts, delete users/posts, basic analytics

DB usage:
- Uses mysql.connector
- Stored procedures: add_new_post(u_id, p_content), update_user_bio(u_id, new_bio), follow_user(follower, following)
- Functions: get_post_count(u_id), get_total_likes(u_id), get_follower_count(u_id), get_following_count(u_id), get_user_engagement_rate(u_id)
- Triggers assumed to exist in DB (new comments/likes/followers notifications, prevent self-follow, cascade deletes)

Notes:
- Configure DB via environment variables: BLOGIFY_DB_HOST, BLOGIFY_DB_USER, BLOGIFY_DB_PASS, BLOGIFY_DB_NAME
- If DB is empty, basic seed can be executed (toggle in SEED_ON_EMPTY)
"""

import os
import sys
import hashlib
import traceback
from datetime import datetime
from typing import Optional, Tuple, Any, List

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

try:
	from PIL import Image, ImageTk
except Exception:
	Image = None
	ImageTk = None

try:
	import mysql.connector as mysql
	from mysql.connector import Error as MySQLError
except Exception as e:
	mysql = None
	MySQLError = Exception

# Optional: charts
try:
	import matplotlib
	matplotlib.use("Agg")
	from matplotlib.figure import Figure
	from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
	Figure = None
	FigureCanvasTkAgg = None

# ===================== CONFIG =====================

CONFIG_FILE = "blogify_config.json"
DB_HOST = os.getenv("BLOGIFY_DB_HOST", "localhost")
DB_PORT = int(os.getenv("BLOGIFY_DB_PORT", "3306"))
DB_USER = os.getenv("BLOGIFY_DB_USER", "root")
DB_PASS = os.getenv("BLOGIFY_DB_PASS", "")
DB_NAME = os.getenv("BLOGIFY_DB_NAME", "blogify")
SEED_ON_EMPTY = True

# Pastel theme
COLORS = {
	# Inspired by Instagram gradient (purple → pink → orange)
	"bg": "#FFF8FB",
	"card": "#FFFFFF",
	"accent": "#E1306C",         # Instagram magenta
	"accent_hover": "#FD1D1D",   # Reddish hover
	"accent_alt": "#F77737",     # Orange accent
	"border": "#F1D4E5",
	"text": "#0F172A",
	"text_muted": "#6B7280",
	"danger": "#EF4444",
	"success": "#22C55E",
	"warning": "#F59E0B",
	"chip": "#FFE4F0",
	"grad_start": "#833AB4",
	"grad_mid": "#E1306C",
	"grad_end": "#F77737",
}

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_H1 = ("Segoe UI", 16, "bold")
FONT_H2 = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 9)


# ===================== DB HELPERS =====================

def load_app_config():
	"""
	Load DB config from JSON file if present; fallback to environment.
	"""
	global DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
	try:
		import json
		if os.path.exists(CONFIG_FILE):
			with open(CONFIG_FILE, "r", encoding="utf-8") as f:
				cfg = json.load(f)
			DB_HOST = cfg.get("host", DB_HOST)
			DB_PORT = int(cfg.get("port", DB_PORT))
			DB_USER = cfg.get("user", DB_USER)
			DB_PASS = cfg.get("password", DB_PASS)
			DB_NAME = cfg.get("database", DB_NAME)
	except Exception as e:
		print("Could not load config:", e, file=sys.stderr)


def save_app_config(host: str, port: int, user: str, password: str, database: str):
	"""
	Save DB config to JSON file.
	"""
	try:
		import json
		with open(CONFIG_FILE, "w", encoding="utf-8") as f:
			json.dump(
				{"host": host, "port": port, "user": user, "password": password, "database": database},
				f, indent=2
			)
	except Exception as e:
		print("Could not save config:", e, file=sys.stderr)


def connect_db(host: Optional[str] = None, port: Optional[int] = None, user: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = None) -> Optional[Any]:
	"""
	Connect to MySQL using mysql.connector.
	Returns a connection or None on failure.
	"""
	if mysql is None:
		messagebox.showerror("Error", "mysql-connector-python is not installed.")
		return None
	try:
		conn = mysql.connect(
			host=host or DB_HOST,
			port=port or DB_PORT,
			user=user or DB_USER,
			password=password or DB_PASS,
			database=database or DB_NAME,
			connection_timeout=10,
			autocommit=True,
		)
		if conn and conn.is_connected():
			return conn
		return None
	except MySQLError as e:
		# Provide detailed feedback for common connection issues
		err_msg = f"Failed to connect to DB:\n{e}\n\nCurrent settings:\nHost: {host or DB_HOST}\nPort: {port or DB_PORT}\nUser: {user or DB_USER}\nDatabase: {database or DB_NAME}"
		messagebox.showerror("DB Connection Error", err_msg)
		return None
	except Exception as e:
		messagebox.showerror("Unexpected Error", f"{e}")
		return conn


def hash_password(password: str) -> str:
	"""
	Hash a password using SHA-256. In production, use a strong hashing scheme (bcrypt/argon2).
	"""
	return hashlib.sha256(password.encode("utf-8")).hexdigest()


def fetch_one(conn, query: str, params: Tuple = ()) -> Optional[Tuple]:
	try:
		with conn.cursor() as cur:
			cur.execute(query, params)
			return cur.fetchone()
	except MySQLError as e:
		print("fetch_one error:", e, file=sys.stderr)
		return None


def fetch_all(conn, query: str, params: Tuple = ()) -> List[Tuple]:
	try:
		with conn.cursor() as cur:
			cur.execute(query, params)
			return cur.fetchall()
	except MySQLError as e:
		print("fetch_all error:", e, file=sys.stderr)
		return []


def execute(conn, query: str, params: Tuple = ()) -> bool:
	try:
		with conn.cursor() as cur:
			cur.execute(query, params)
		conn.commit()
		return True
	except MySQLError as e:
		print("execute error:", e, file=sys.stderr)
		return False


def call_procedure(conn, name: str, args: Tuple) -> bool:
	"""
	Call a stored procedure by name with given args.
	"""
	try:
		with conn.cursor() as cur:
			cur.callproc(name, args)
		conn.commit()
		return True
	except MySQLError as e:
		messagebox.showerror("DB Error", f"Procedure {name} failed:\n{e}")
		return False


def call_function_scalar(conn, func_sql: str, params: Tuple) -> Optional[Any]:
	"""
	Call a function via SELECT e.g., SELECT get_post_count(%s)
	"""
	try:
		with conn.cursor() as cur:
			cur.execute(func_sql, params)
			row = cur.fetchone()
			return row[0] if row else None
	except MySQLError as e:
		print("call_function_scalar error:", e, file=sys.stderr)
		return None


# ===================== UI UTILITIES =====================

ASSETS_DIR = "blogify_assets"
IMAGE_MAP_FILE = "blogify_images.json"

def ensure_assets_dir():
	try:
		if not os.path.isdir(ASSETS_DIR):
			os.makedirs(ASSETS_DIR, exist_ok=True)
	except Exception as e:
		print("ensure_assets_dir:", e, file=sys.stderr)

def load_image_map() -> dict:
	try:
		import json
		if os.path.exists(IMAGE_MAP_FILE):
			with open(IMAGE_MAP_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
	except Exception as e:
		print("load_image_map:", e, file=sys.stderr)
	return {}

def save_image_map(img_map: dict):
	try:
		import json
		with open(IMAGE_MAP_FILE, "w", encoding="utf-8") as f:
			json.dump(img_map, f, indent=2)
	except Exception as e:
		print("save_image_map:", e, file=sys.stderr)

def generate_placeholder_image(path: str, title: str):
	"""
	Create a colorful placeholder image if no image chosen.
	"""
	if Image is None:
		return
	try:
		from random import randint
		w, h = 900, 420
		bg = (randint(120,220), randint(120,220), randint(120,220))
		img = Image.new("RGB", (w, h), bg)
		try:
			from PIL import ImageDraw, ImageFont
			draw = ImageDraw.Draw(img)
			text = title[:20] or "Blogify"
			font = ImageFont.load_default()
			tw, th = draw.textsize(text, font=font)
			draw.text(((w-tw)//2, (h-th)//2), text, fill=(255,255,255), font=font)
		except Exception:
			pass
		img.save(path)
	except Exception as e:
		print("generate_placeholder_image:", e, file=sys.stderr)

def get_or_create_logo() -> Optional[str]:
	"""
	Create or return a beautiful logo image for Blogify.
	"""
	if Image is None:
		return None
	try:
		ensure_assets_dir()
		logo_path = os.path.join(ASSETS_DIR, "logo.png")
		if os.path.exists(logo_path):
			return logo_path
		# Create beautiful circular logo
		w, h = 350, 350
		img = Image.new("RGB", (w, h), (255, 255, 255))
		from PIL import ImageDraw, ImageFilter
		draw = ImageDraw.Draw(img)
		
		center_x, center_y = w // 2, h // 2
		
		# Draw beautiful gradient circles (Instagram-inspired)
		# Outer circle - purple
		draw.ellipse([20, 20, w-20, h-20], fill=(139, 69, 237), outline=None)
		# Middle circle - pink
		draw.ellipse([60, 60, w-60, h-60], fill=(255, 105, 180), outline=None)
		# Inner circle - light pink
		draw.ellipse([100, 100, w-100, h-100], fill=(255, 182, 193), outline=None)
		# Center circle - white
		draw.ellipse([130, 130, w-130, h-130], fill=(255, 255, 255), outline=None)
		
		# Add "B" text in center (Blogify initial)
		try:
			from PIL import ImageFont
			try:
				font = ImageFont.truetype("arial.ttf", 120) if os.name == "nt" else ImageFont.load_default()
			except:
				try:
					font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 120)
				except:
					font = ImageFont.load_default()
			
			# Draw "B" letter
			text = "B"
			try:
				bbox = draw.textbbox((0, 0), text, font=font)
				text_w = bbox[2] - bbox[0]
				text_h = bbox[3] - bbox[1]
			except:
				# Fallback for older PIL
				try:
					text_w, text_h = draw.textsize(text, font=font)
				except:
					text_w, text_h = 80, 100
			
			text_x = center_x - text_w // 2
			text_y = center_y - text_h // 2 - 10
			draw.text((text_x, text_y), text, fill=(139, 69, 237), font=font)
		except Exception as e:
			# Fallback: draw a colored circle
			draw.ellipse([center_x-35, center_y-35, center_x+35, center_y+35], fill=(139, 69, 237), outline=None)
		
		# Add subtle shadow effect
		try:
			shadow = img.filter(ImageFilter.GaussianBlur(radius=3))
			img.paste(shadow, (5, 5))
			img.paste(img, (0, 0))
		except:
			pass
		
		img.save(logo_path, format="PNG", optimize=True)
		return logo_path
	except Exception as e:
		print("create_logo error:", e, file=sys.stderr)
	return None

def get_or_create_banner() -> Optional[str]:
	"""
	Create or return a hero banner image path for the login/landing screen.
	"""
	if Image is None:
		return None
	try:
		ensure_assets_dir()
		banner_path = os.path.join(ASSETS_DIR, "banner.png")
		if os.path.exists(banner_path):
			return banner_path
		# build gradient banner
		w, h = 720, 520
		img = Image.new("RGB", (w, h), (255, 255, 255))
		from PIL import ImageDraw
		draw = ImageDraw.Draw(img)
		start = COLORS["grad_start"]; mid = COLORS["grad_mid"]; end = COLORS["grad_end"]
		def hex_to_rgb(hx): return tuple(int(hx[i:i+2], 16) for i in (1,3,5))
		def blend(a,b,t): return tuple(int(a[k] + (b[k]-a[k])*t) for k in range(3))
		c1, c2, c3 = hex_to_rgb(start), hex_to_rgb(mid), hex_to_rgb(end)
		for y in range(h):
			ratio = y / (h-1 or 1)
			if ratio < 0.5:
				t = ratio / 0.5
				c = blend(c1, c2, t)
			else:
				t = (ratio - 0.5) / 0.5
				c = blend(c2, c3, t)
			draw.line([(0, y), (w, y)], fill=c, width=1)
		# overlay subtle shapes
		try:
			from PIL import ImageFilter
			ov = Image.new("RGBA", (w, h), (255, 255, 255, 0))
			ov_draw = ImageDraw.Draw(ov)
			ov_draw.ellipse((w*0.6, -h*0.2, w*1.2, h*0.4), fill=(255,255,255,38))
			ov_draw.rectangle((int(w*0.05), int(h*0.65), int(w*0.55), int(h*0.95)), fill=(255,255,255,28))
			ov = ov.filter(ImageFilter.GaussianBlur(12))
			img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
		except Exception:
			pass
		# add title text
		try:
			from PIL import ImageFont
			draw = ImageDraw.Draw(img)
			title = "Welcome to Blogify"
			sub = "Share your moments • Connect • Explore"
			font_big = ImageFont.truetype("arial.ttf", 40) if os.name == "nt" else ImageFont.load_default()
			font_small = ImageFont.truetype("arial.ttf", 18) if os.name == "nt" else ImageFont.load_default()
			tw, th = draw.textsize(title, font=font_big)
			sw, sh = draw.textsize(sub, font=font_small)
			draw.text(((w - tw)//2, int(h*0.30)), title, fill=(255,255,255), font=font_big)
			draw.text(((w - sw)//2, int(h*0.30)+th+10), sub, fill=(255,255,255), font=font_small)
		except Exception:
			pass
		img.save(banner_path, format="PNG", optimize=True)
		return banner_path
	except Exception as e:
		print("get_or_create_banner:", e, file=sys.stderr)
		return None

class RoundedButton(ttk.Frame):
	"""
	A rounded-looking button using ttk with hover effect.
	"""
	def __init__(self, master, text: str, command, width: int = 16, bg: Optional[str] = None, hover_bg: Optional[str] = None, fg: str = "white"):
		super().__init__(master, padding=1)
		self.command = command
		self._bg = bg or COLORS["accent"]
		self._hover_bg = hover_bg or COLORS["accent_hover"]
		self.btn = tk.Label(
			self,
			text=text,
			bg=self._bg,
			fg=fg,
			font=FONT_BODY,
			padx=14,
			pady=8,
			cursor="hand2",
			bd=0,
			relief="flat",
		)
		self.btn.pack(fill="both", expand=True)
		self.btn.bind("<Button-1>", lambda e: self.command())
		self.btn.bind("<Enter>", self._on_enter)
		self.btn.bind("<Leave>", self._on_leave)

	def _on_enter(self, _):
		self.btn.configure(bg=self._hover_bg)

	def _on_leave(self, _):
		self.btn.configure(bg=self._bg)


def make_scrollable(parent) -> Tuple[tk.Canvas, ttk.Scrollbar, tk.Frame]:
	"""
	Create a vertical scrollable area.
	"""
	container = ttk.Frame(parent)
	container.pack(fill="both", expand=True)
	canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
	scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
	scrollable_frame = ttk.Frame(canvas)

	scrollable_frame.bind(
		"<Configure>",
		lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
	)
	canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
	canvas.configure(yscrollcommand=scrollbar.set)

	canvas.pack(side="left", fill="both", expand=True)
	scrollbar.pack(side="right", fill="y")

	# mouse wheel
	def _on_mousewheel(event):
		canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
	canvas.bind_all("<MouseWheel>", _on_mousewheel)

	return canvas, scrollbar, scrollable_frame


class AddPostDialog(tk.Toplevel):
	"""
	Dialog for creating a new post with optional image attachment.
	"""
	def __init__(self, parent, on_submit):
		super().__init__(parent)
		self.title("Create Post")
		self.configure(bg=COLORS["bg"])
		self.resizable(False, False)
		self.selected_path = None
		self.preview_imgtk = None
		self.on_submit = on_submit

		body = ttk.Frame(self, padding=14)
		body.pack(fill="both", expand=True)
		ttk.Label(body, text="New Post", style="H1.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,10))

		ttk.Label(body, text="Content").grid(row=1, column=0, sticky="nw")
		self.txt = tk.Text(body, height=6, width=60, bd=0, relief="flat", wrap="word")
		self.txt.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

		ttk.Label(body, text="Image").grid(row=2, column=0, sticky="w")
		self.img_preview = tk.Label(body, bg=COLORS["card"], width=60, height=12, bd=1, relief="groove")
		self.img_preview.grid(row=2, column=1, sticky="ew", pady=4)
		RoundedButton(body, "Choose Image", self._choose_image).grid(row=2, column=2, sticky="w", padx=6)

		btns = ttk.Frame(body); btns.grid(row=3, column=0, columnspan=3, pady=(10,0), sticky="e")
		RoundedButton(btns, "Post", self._submit).pack(side="left", padx=4)
		RoundedButton(btns, "Cancel", self.destroy).pack(side="left", padx=4)

		self.grab_set()
		self.transient(parent)

	def _choose_image(self):
		from tkinter import filedialog
		fp = filedialog.askopenfilename(title="Select Image", filetypes=[("Images",".png;.jpg;.jpeg;.bmp;*.gif")])
		if not fp:
			return
		self.selected_path = fp
		if Image:
			try:
				img = Image.open(fp)
				img.thumbnail((600, 300))
				self.preview_imgtk = ImageTk.PhotoImage(img)
				self.img_preview.configure(image=self.preview_imgtk, text="")
			except Exception:
				self.img_preview.configure(text="Preview unavailable")
		else:
			self.img_preview.configure(text=os.path.basename(fp))

	def _submit(self):
		content = self.txt.get("1.0", "end-1c").strip()
		self.on_submit(content, self.selected_path)
		self.destroy()


# ===================== MAIN APP =====================

class DBSettingsDialog(tk.Toplevel):
	"""
	Popup dialog to configure database connection settings.
	"""
	def __init__(self, parent, on_save):
		super().__init__(parent)
		self.title("Database Settings")
		self.configure(bg=COLORS["bg"])
		self.resizable(False, False)
		self.on_save = on_save

		body = ttk.Frame(self, padding=14)
		body.pack(fill="both", expand=True)
		ttk.Label(body, text="Configure MySQL Connection", style="H1.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))
		ttk.Label(body, text="Host").grid(row=1, column=0, sticky="w"); self.e_host = ttk.Entry(body, width=28); self.e_host.grid(row=1, column=1, sticky="ew", pady=3)
		ttk.Label(body, text="Port").grid(row=2, column=0, sticky="w"); self.e_port = ttk.Entry(body, width=28); self.e_port.grid(row=2, column=1, sticky="ew", pady=3)
		ttk.Label(body, text="User").grid(row=3, column=0, sticky="w"); self.e_user = ttk.Entry(body, width=28); self.e_user.grid(row=3, column=1, sticky="ew", pady=3)
		ttk.Label(body, text="Password").grid(row=4, column=0, sticky="w"); self.e_pass = ttk.Entry(body, width=28, show="*"); self.e_pass.grid(row=4, column=1, sticky="ew", pady=3)
		ttk.Label(body, text="Database").grid(row=5, column=0, sticky="w"); self.e_db = ttk.Entry(body, width=28); self.e_db.grid(row=5, column=1, sticky="ew", pady=3)

		# Fill current values
		self.e_host.insert(0, DB_HOST)
		self.e_port.insert(0, str(DB_PORT))
		self.e_user.insert(0, DB_USER)
		self.e_pass.insert(0, DB_PASS)
		self.e_db.insert(0, DB_NAME)

		btns = ttk.Frame(body); btns.grid(row=6, column=0, columnspan=2, pady=(10,0), sticky="e")
		RoundedButton(btns, "Save", self._save).pack(side="left", padx=4)
		RoundedButton(btns, "Cancel", self.destroy).pack(side="left", padx=4)

		self.grab_set()
		self.transient(parent)

	def _save(self):
		try:
			host = self.e_host.get().strip() or "localhost"
			port = int(self.e_port.get().strip() or "3306")
			user = self.e_user.get().strip() or "root"
			password = self.e_pass.get()
			database = self.e_db.get().strip() or "blogify"
		except ValueError:
			messagebox.showerror("Invalid", "Port must be a number.")
			return
		save_app_config(host, port, user, password, database)
		# Update globals
		global DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
		DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME = host, port, user, password, database
		if callable(self.on_save):
			self.on_save(host, port, user, password, database)
		self.destroy()


class BlogifyApp:
	"""
	Main application class.
	"""
	def __init__(self, root: tk.Tk):
		self.root = root
		self.root.title("Blogify App")
		self.root.geometry("1000x720")
		self.root.configure(bg=COLORS["bg"])
		load_app_config()
		self.conn = connect_db()
		self.current_user = None  # (user_id, username, is_admin)

		self._apply_style()
		if self.conn:
			self._maybe_seed()
			self._ensure_admin_account()
		# Always show login UI, even if not connected
		self.show_login()
		# If not connected, auto-open DB settings so users can fix it immediately
		if not self.conn:
			def on_save(host, port, user, password, database):
				self.conn = connect_db(host, port, user, password, database)
				# Refresh UI to reflect connection state
				self.show_login()
			self.root.after(200, lambda: DBSettingsDialog(self.root, on_save))

	def _apply_style(self):
		style = ttk.Style(self.root)
		try:
			style.theme_use("clam")
		except Exception:
			pass
		style.configure("TFrame", background=COLORS["bg"])
		style.configure("Card.TFrame", background=COLORS["card"], relief="flat", borderwidth=0)
		style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_BODY)
		style.configure("Muted.TLabel", foreground=COLORS["text_muted"])
		style.configure("H1.TLabel", font=FONT_H1)
		style.configure("H2.TLabel", font=FONT_H2)
		style.configure("Title.TLabel", font=FONT_TITLE, foreground=COLORS["accent"])
		style.configure("TButton", font=FONT_BODY, padding=6)
		style.configure("Danger.TButton", foreground="white", background=COLORS["danger"])
		style.map("TButton", background=[("active", COLORS["accent_hover"])])

	def _clear_root(self):
		for w in self.root.winfo_children():
			w.destroy()

	def _navbar(self):
		# Gradient navbar
		bar_h = 68
		wrap = ttk.Frame(self.root)
		wrap.pack(fill="x")
		canvas = tk.Canvas(wrap, height=bar_h, highlightthickness=0, bd=0)
		canvas.pack(fill="x")
		# draw horizontal gradient
		def draw_gradient():
			canvas.delete("grad")
			width = canvas.winfo_width() or self.root.winfo_width()
			steps = max(1, width // 3)
			from_colors = [COLORS["grad_start"], COLORS["grad_mid"], COLORS["grad_end"]]
			# interpolate across width
			for i in range(steps):
				ratio = i / steps
				# blend from start→mid for first half, mid→end for second half
				if ratio < 0.5:
					t = ratio / 0.5
					c1, c2 = from_colors[0], from_colors[1]
				else:
					t = (ratio - 0.5) / 0.5
					c1, c2 = from_colors[1], from_colors[2]
				def hex_to_rgb(h): return tuple(int(h[j:j+2], 16) for j in (1,3,5))
				def blend(a,b,t): return tuple(int(a[k] + (b[k]-a[k])*t) for k in range(3))
				a = hex_to_rgb(c1); b = hex_to_rgb(c2); c = blend(a,b,t)
				color = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
				x0 = int(i * (width/steps))
				x1 = int((i+1) * (width/steps)) + 1
				canvas.create_rectangle(x0, 0, x1, bar_h, fill=color, outline="", tags="grad")
			# reposition title and buttons
			try:
				canvas.coords(self._nav_title_id, 16, bar_h//2)
				canvas.coords(self._nav_btns_id, width - 16, bar_h//2)
			except Exception:
				pass
		canvas.bind("<Configure>", lambda e: draw_gradient())

		# overlay title and buttons
		title = tk.Label(canvas, text="Blogify", fg="white", bg=COLORS["grad_mid"], font=FONT_TITLE)
		btns = ttk.Frame(canvas)
		for text, cmd in [
			("Home", self.create_user_dashboard if not self._is_admin() else self.create_admin_dashboard),
			("Search", self.show_search),
			("Profile", self.show_profile),
			("Notifications", self.view_notifications),
			("Logout", self.logout),
		]:
			RoundedButton(btns, text, cmd, bg="#ffffff", hover_bg="#FFE4EC", fg=COLORS["accent"]).pack(side="left", padx=6)
		# place on canvas
		self._nav_title_id = canvas.create_window(16, bar_h//2, window=title, anchor="w")
		self._nav_btns_id = canvas.create_window(self.root.winfo_width()-16, bar_h//2, window=btns, anchor="e")

	def _is_admin(self) -> bool:
		return bool(self.current_user and self.current_user[2])

	def _maybe_seed(self):
		"""
		Optionally seed minimal data if tables are empty.
		Only runs if SEED_ON_EMPTY is True. Requires schema to exist.
		"""
		if not SEED_ON_EMPTY:
			return
		try:
			row = fetch_one(self.conn, "SELECT COUNT(*) FROM user")
			if not row:
				return
			if row[0] == 0:
				# create a default admin and user
				admin_pw = hash_password("admin123")
				user_pw = hash_password("user123")
				execute(self.conn, "INSERT INTO user (user_id, username, email, password, bio, created_at) VALUES (1,'admin','admin@blogify.local',%s,'Admin account',NOW())", (admin_pw,))
				execute(self.conn, "INSERT INTO user (user_id, username, email, password, bio, created_at) VALUES (2,'harini','harini@example.com',%s,'Hello, I am Harini!',NOW())", (user_pw,))
				# sample posts
				execute(self.conn, "INSERT INTO post (post_id, user_id, content, created_at) VALUES (1,2,'Welcome to Blogify! 🚀',NOW())")
				execute(self.conn, "INSERT INTO post (post_id, user_id, content, created_at) VALUES (2,2,'Coffee and code ☕💻',NOW())")
		except MySQLError as e:
			print("Seed skipped:", e, file=sys.stderr)

	def _ensure_admin_account(self):
		if not self.conn:
			return
		admin = fetch_one(self.conn, "SELECT user_id FROM user WHERE email=%s OR username=%s", ("admin@blogify.local", "admin"))
		if not admin:
			admin_pw = hash_password("admin123")
			execute(
				self.conn,
				"INSERT INTO user (username, email, password, bio, created_at) VALUES (%s,%s,%s,%s,NOW())",
				("admin", "admin@blogify.local", admin_pw, "Administrator account"),
			)
	# ===================== AUTH =====================
	def show_login(self, active_tab: str = "login"):
		"""Beautiful modern login/registration screen with logo."""
		self._clear_root()
		
		# Simple light background instead of gradient
		main_container = tk.Frame(self.root, bg="#f8f9fa", highlightthickness=0)
		main_container.pack(fill="both", expand=True)
		
		# Split screen container
		split_container = tk.Frame(main_container, bg="#f8f9fa", highlightthickness=0)
		split_container.pack(fill="both", expand=True, padx=40, pady=40)
		split_container.grid_columnconfigure(0, weight=1)
		split_container.grid_columnconfigure(1, weight=1)
		split_container.grid_rowconfigure(0, weight=1)
		
		# Left side - Logo and hero section
		left_frame = tk.Frame(split_container, bg="#ffffff", relief="flat", width=500)
		left_frame.grid(row=0, column=0, padx=(0, 20), pady=20, sticky="nsew")
		left_frame.pack_propagate(False)
		
		# Hero content with padding
		hero_content = tk.Frame(left_frame, bg="#ffffff")
		hero_content.pack(fill="both", expand=True, padx=50, pady=60)
		
		# Logo image - prominent display
		logo_path = get_or_create_logo()
		if logo_path and Image and os.path.exists(logo_path):
			try:
				img = Image.open(logo_path)
				img.thumbnail((280, 280), Image.Resampling.LANCZOS)
				logo_imgtk = ImageTk.PhotoImage(img)
				logo_label = tk.Label(hero_content, image=logo_imgtk, bg="#ffffff", bd=0)
				logo_label.image = logo_imgtk
				logo_label.pack(pady=(20, 30))
			except Exception as e:
				# Fallback to text logo
				logo_text = tk.Label(hero_content, text="🌟", font=("Segoe UI", 80), bg="#ffffff", fg=COLORS["accent"])
				logo_text.pack(pady=(40, 20))
		else:
			# Fallback: text logo
			logo_text = tk.Label(hero_content, text="🌟", font=("Segoe UI", 80), bg="#ffffff", fg=COLORS["accent"])
			logo_text.pack(pady=(40, 20))
		
		# App title
		title_label = tk.Label(hero_content, text="Blogify", 
		                     font=("Segoe UI", 42, "bold"), 
		                     bg="#ffffff", fg=COLORS["accent"])
		title_label.pack(pady=(0, 15))
		
		subtitle_label = tk.Label(hero_content, text="Share Your Stories", 
		                         font=("Segoe UI", 18), 
		                         bg="#ffffff", fg=COLORS["text_muted"])
		subtitle_label.pack(pady=(0, 50))
		
		# Feature icons
		icons_frame = tk.Frame(hero_content, bg="#ffffff")
		icons_frame.pack(pady=20)
		features = [("📸", "Posts"), ("❤", "Likes"), ("💬", "Comments"), ("👥", "Follow")]
		for i, (emoji, label) in enumerate(features):
			feat = tk.Frame(icons_frame, bg="#ffffff")
			feat.grid(row=0, column=i, padx=12)
			tk.Label(feat, text=emoji, font=("Segoe UI", 24), bg="#ffffff").pack()
			tk.Label(feat, text=label, font=("Segoe UI", 10), bg="#ffffff", fg=COLORS["text_muted"]).pack()
		
		# Features list
		features_list = tk.Frame(hero_content, bg="#ffffff")
		features_list.pack(pady=40, anchor="center")
		feature_items = [
			("✨", "Create beautiful posts"),
			("💝", "Connect with friends"),
			("📊", "Track engagement"),
			("🎨", "Express yourself"),
		]
		for emoji, text in feature_items:
			item = tk.Frame(features_list, bg="#ffffff")
			item.pack(anchor="center", pady=8)
			tk.Label(item, text=emoji, font=("Segoe UI", 18), bg="#ffffff").pack(side="left", padx=(0, 12))
			tk.Label(item, text=text, font=("Segoe UI", 13), bg="#ffffff", fg=COLORS["text"]).pack(side="left")
		
		# Right side - Login card
		login_frame = tk.Frame(split_container, bg="#ffffff", relief="flat", width=400)
		login_frame.grid(row=0, column=1, padx=(20, 0), pady=20, sticky="nsew")
		login_frame.pack_propagate(False)
		
		# Login/signup card content
		login_content = tk.Frame(login_frame, bg="#ffffff")
		login_content.pack(fill="both", expand=True, padx=40, pady=32)
		
		# Welcome text
		welcome_label = tk.Label(login_content, text="Welcome Back", 
		                        font=("Segoe UI", 32, "bold"), 
		                        bg="#ffffff", fg=COLORS["text"])
		welcome_label.pack(pady=(10, 5))
		
		signin_label = tk.Label(login_content, text="Sign in to continue", 
		                       font=("Segoe UI", 13), 
		                       bg="#ffffff", fg=COLORS["text_muted"])
		signin_label.pack(pady=(0, 35))
		
		# DB status (subtle, top right)
		status_frame = tk.Frame(login_content, bg="#ffffff")
		status_frame.pack(fill="x", pady=(0, 20))
		if self.conn:
			status_text = f"✓ Connected"
			status_color = COLORS["success"]
		else:
			status_text = "✗ Not connected"
			status_color = COLORS["danger"]
		status_label = tk.Label(status_frame, text=status_text, 
		                       font=("Segoe UI", 9), 
		                       bg="#ffffff", fg=status_color)
		status_label.pack(side="left")
		db_settings_btn = tk.Button(status_frame, text="DB Settings", 
		                          font=("Segoe UI", 8), 
		                          bg="#f0f0f0", fg=COLORS["text"], 
		                          relief="flat", cursor="hand2", bd=0,
		                          command=lambda: DBSettingsDialog(self.root, lambda h,p,u,pw,db: self._reconnect(h,p,u,pw,db)))
		db_settings_btn.pack(side="right")
		
		# Tabs for sign-in and sign-up
		tabs = ttk.Notebook(login_content)
		login_tab = tk.Frame(tabs, bg="#ffffff")
		signup_tab = tk.Frame(tabs, bg="#ffffff")
		tabs.add(login_tab, text="Sign In")
		tabs.add(signup_tab, text="Create Account")
		tabs.pack(fill="both", expand=True, pady=(10, 0))
		
		# Login tab contents
		inputs_frame = tk.Frame(login_tab, bg="#ffffff")
		inputs_frame.pack(fill="both", expand=True, pady=(10, 0))
		
		user_label = tk.Label(inputs_frame, text="Username or Email", 
		                     font=("Segoe UI", 11, "bold"), 
		                     bg="#ffffff", fg=COLORS["text"], anchor="w")
		user_label.pack(fill="x", pady=(0, 8))
		u_entry = tk.Entry(inputs_frame, font=("Segoe UI", 13), 
		                  relief="flat", bd=2, bg="#f8f9fa", 
		                  fg=COLORS["text"], insertbackground=COLORS["accent"],
		                  highlightthickness=2, highlightcolor=COLORS["accent"],
		                  highlightbackground="#e0e0e0")
		u_entry.pack(fill="x", pady=(0, 20), ipady=10)
		u_entry.bind("<FocusIn>", lambda e: u_entry.configure(highlightbackground=COLORS["accent"]))
		u_entry.bind("<FocusOut>", lambda e: u_entry.configure(highlightbackground="#e0e0e0"))
		
		pass_label = tk.Label(inputs_frame, text="Password", 
		                     font=("Segoe UI", 11, "bold"), 
		                     bg="#ffffff", fg=COLORS["text"], anchor="w")
		pass_label.pack(fill="x", pady=(0, 8))
		p_entry = tk.Entry(inputs_frame, font=("Segoe UI", 13), show="*", 
		                  relief="flat", bd=2, bg="#f8f9fa", 
		                  fg=COLORS["text"], insertbackground=COLORS["accent"],
		                  highlightthickness=2, highlightcolor=COLORS["accent"],
		                  highlightbackground="#e0e0e0")
		p_entry.pack(fill="x", pady=(0, 25), ipady=10)
		p_entry.bind("<FocusIn>", lambda e: p_entry.configure(highlightbackground=COLORS["accent"]))
		p_entry.bind("<FocusOut>", lambda e: p_entry.configure(highlightbackground="#e0e0e0"))
		
		def on_login():
			self._login(u_entry.get().strip(), p_entry.get().strip())
		
		login_btn = tk.Button(inputs_frame, text="Sign In", 
		                     font=("Segoe UI", 15, "bold"), 
		                     bg=COLORS["accent"], fg="#ffffff", 
		                     relief="flat", cursor="hand2", bd=0,
		                     activebackground=COLORS["accent_hover"], 
		                     activeforeground="#ffffff",
		                     command=on_login, padx=30, pady=14)
		login_btn.pack(fill="x", pady=10)
		
		u_entry.bind("<Return>", lambda e: on_login())
		p_entry.bind("<Return>", lambda e: on_login())
		
		# Signup tab contents
		signup_frame = tk.Frame(signup_tab, bg="#ffffff")
		signup_frame.pack(fill="both", expand=True, pady=(16, 0))
		
		su_user_label = tk.Label(signup_frame, text="Username", font=("Segoe UI", 11, "bold"),
		                         bg="#ffffff", fg=COLORS["text"], anchor="w")
		su_user_label.pack(fill="x", pady=(0, 8))
		su_user_entry = tk.Entry(signup_frame, font=("Segoe UI", 12), relief="flat", bd=2,
		                         bg="#f8f9fa", fg=COLORS["text"], insertbackground=COLORS["accent"],
		                         highlightthickness=2, highlightcolor=COLORS["accent"],
		                         highlightbackground="#e0e0e0")
		su_user_entry.pack(fill="x", pady=(0, 16), ipady=8)
		
		su_email_label = tk.Label(signup_frame, text="Email", font=("Segoe UI", 11, "bold"),
		                          bg="#ffffff", fg=COLORS["text"], anchor="w")
		su_email_label.pack(fill="x", pady=(0, 8))
		su_email_entry = tk.Entry(signup_frame, font=("Segoe UI", 12), relief="flat", bd=2,
		                          bg="#f8f9fa", fg=COLORS["text"], insertbackground=COLORS["accent"],
		                          highlightthickness=2, highlightcolor=COLORS["accent"],
		                          highlightbackground="#e0e0e0")
		su_email_entry.pack(fill="x", pady=(0, 16), ipady=8)
		
		su_pass_label = tk.Label(signup_frame, text="Password", font=("Segoe UI", 11, "bold"),
		                         bg="#ffffff", fg=COLORS["text"], anchor="w")
		su_pass_label.pack(fill="x", pady=(0, 8))
		su_pass_entry = tk.Entry(signup_frame, font=("Segoe UI", 12), show="*", relief="flat", bd=2,
		                         bg="#f8f9fa", fg=COLORS["text"], insertbackground=COLORS["accent"],
		                         highlightthickness=2, highlightcolor=COLORS["accent"],
		                         highlightbackground="#e0e0e0")
		su_pass_entry.pack(fill="x", pady=(0, 16), ipady=8)
		
		su_bio_label = tk.Label(signup_frame, text="Bio (optional)", font=("Segoe UI", 11, "bold"),
		                        bg="#ffffff", fg=COLORS["text"], anchor="w")
		su_bio_label.pack(fill="x", pady=(0, 8))
		su_bio_entry = tk.Entry(signup_frame, font=("Segoe UI", 12), relief="flat", bd=2,
		                        bg="#f8f9fa", fg=COLORS["text"], insertbackground=COLORS["accent"],
		                        highlightthickness=2, highlightcolor=COLORS["accent"],
		                        highlightbackground="#e0e0e0")
		su_bio_entry.pack(fill="x", pady=(0, 20), ipady=8)
		
		def on_signup():
			self._register_user(
				su_user_entry.get(),
				su_email_entry.get(),
				su_pass_entry.get(),
				su_bio_entry.get(),
			)
		
		signup_btn = tk.Button(signup_frame, text="Create Account",
		                       font=("Segoe UI", 15, "bold"),
		                       bg=COLORS["accent"], fg="#ffffff",
		                       relief="flat", cursor="hand2", bd=0,
		                       activebackground=COLORS["accent_hover"],
		                       activeforeground="#ffffff",
		                       command=on_signup, padx=30, pady=14)
		signup_btn.pack(fill="x", pady=10)
		
		su_user_entry.bind("<Return>", lambda e: on_signup())
		su_email_entry.bind("<Return>", lambda e: on_signup())
		su_pass_entry.bind("<Return>", lambda e: on_signup())
		su_bio_entry.bind("<Return>", lambda e: on_signup())
		
		def switch_to_signup():
			tabs.select(signup_tab)
			signin_label.configure(text="Create an account to join the community")
		
		def switch_to_login():
			tabs.select(login_tab)
			signin_label.configure(text="Sign in to continue")
		
		# Divider
		divider_frame = tk.Frame(login_content, bg="#ffffff")
		divider_frame.pack(fill="x", pady=18)
		tk.Frame(divider_frame, bg="#e0e0e0", height=1).pack(fill="x", side="left", expand=True)
		tk.Label(divider_frame, text="Need a new account?", font=("Segoe UI", 11), 
		        bg="#ffffff", fg=COLORS["text_muted"]).pack(side="left", padx=12)
		tk.Frame(divider_frame, bg="#e0e0e0", height=1).pack(fill="x", side="left", expand=True)
		
		register_btn = tk.Button(login_content, text="Create New Account", 
		                        font=("Segoe UI", 13), 
		                        bg="#f8f9fa", fg=COLORS["accent"], 
		                        relief="flat", cursor="hand2", bd=0,
		                        activebackground="#e9ecef", 
		                        activeforeground=COLORS["accent"],
		                        command=switch_to_signup, padx=30, pady=12)
		register_btn.pack(fill="x", pady=5)
		
		# Note about admin
		admin_note = tk.Label(login_content, 
		                     text="💡 Admin: Login with admin@blogify.local", 
		                     font=("Segoe UI", 9), 
		                     bg="#ffffff", fg=COLORS["text_muted"])
		admin_note.pack(pady=(20, 0))
		
		if active_tab.lower() == "signup":
			tabs.select(signup_tab)
			signin_label.configure(text="Create an account to join the community")
		else:
			tabs.select(login_tab)
			signin_label.configure(text="Sign in to continue")

	def _reconnect(self, host, port, user, password, database):
		self.conn = connect_db(host, port, user, password, database)
		if self.conn:
			messagebox.showinfo("Connected", "Database connection successful.")
			self.show_login()
		else:
			messagebox.showerror("Connection Failed", "Please check settings and try again.")

	def show_register(self):
		"""Backward compatibility: route to signup tab."""
		self.show_login(active_tab="signup")

	def _login(self, email_or_username: str, password: str):
		"""Login function - auto-detects admin status based on email/username."""
		if not email_or_username or not password:
			messagebox.showwarning("Missing", "Please enter credentials.")
			return
		if not self.conn:
			messagebox.showerror("Error", "Database not connected. Please configure database settings.")
			return

		email_or_username = email_or_username.strip()
		password = password.strip()
		row = fetch_one(self.conn, "SELECT user_id, username, email, password FROM user WHERE email=%s OR username=%s", (email_or_username, email_or_username))
		if not row:
			messagebox.showerror("Login failed", "User not found.")
			return

		user_id, username, email, stored_hash = row
		pw_hash = hash_password(password)

		if not stored_hash:
			messagebox.showerror("Login failed", "Password is missing for this account. Please reset it.")
			return
		if stored_hash.strip() != pw_hash.strip():
			# Fallback: allow legacy plaintext matches if database contains unhashed values
			if stored_hash != password:
				messagebox.showerror("Login failed", "Invalid password.")
				return

		# Auto-detect admin: check if email is admin@blogify.local or username is 'admin'
		is_admin = (email.lower() == "admin@blogify.local" or username.lower() == "admin")
		self.current_user = (user_id, username, is_admin)
		messagebox.showinfo("Success", f"Welcome {username}!" + (" (Admin)" if is_admin else ""))
		if is_admin:
			self.create_admin_dashboard()
		else:
			self.create_user_dashboard()

	def logout(self):
		self.current_user = None
		self.show_login()

	def _get_user_metrics(self, uid: int) -> dict:
		metrics = {
			"posts": 0,
			"likes": 0,
			"followers": 0,
			"following": 0,
			"engagement": 0.0,
		}
		if not self.conn:
			return metrics
		try:
			row = fetch_one(self.conn, "SELECT COUNT(*) FROM post WHERE user_id=%s", (uid,))
			metrics["posts"] = row[0] if row else 0

			row = fetch_one(self.conn, "SELECT COUNT(*) FROM postlike WHERE post_id IN (SELECT post_id FROM post WHERE user_id=%s)", (uid,))
			metrics["likes"] = row[0] if row else 0

			row = fetch_one(self.conn, "SELECT COUNT(*) FROM follow WHERE following_id=%s", (uid,))
			metrics["followers"] = row[0] if row else 0

			row = fetch_one(self.conn, "SELECT COUNT(*) FROM follow WHERE follower_id=%s", (uid,))
			metrics["following"] = row[0] if row else 0

			posts = metrics["posts"] or 1
			metrics["engagement"] = round(min(100.0, (metrics["likes"] + metrics["followers"]) * 5 / posts), 1)
		except Exception as e:
			print("metrics error:", e, file=sys.stderr)
		return metrics

	def _register_user(self, username: str, email: str, password: str, bio: str):
		username = username.strip()
		email = email.strip()
		password = password.strip()
		bio = bio.strip()

		if not username or not email or not password:
			messagebox.showwarning("Missing", "Please fill required fields.")
			return
		if "@" not in email or "." not in email.split("@")[-1]:
			messagebox.showwarning("Invalid Email", "Please enter a valid email address.")
			return
		if len(password) < 4:
			messagebox.showwarning("Weak Password", "Password must be at least 4 characters.")
			return
		if not self.conn:
			messagebox.showerror("Error", "Database not connected.")
			return

		existing = fetch_one(self.conn, "SELECT user_id FROM user WHERE username=%s OR email=%s", (username, email))
		if existing:
			messagebox.showerror("Error", "Username or email already exists.")
			return

		pw_hash = hash_password(password)
		ok = execute(self.conn, "INSERT INTO user (username, email, password, bio, created_at) VALUES (%s,%s,%s,%s,NOW())", (username, email, pw_hash, bio))
		if ok:
			messagebox.showinfo("Success", "Account created. You can login now.")
			self.show_login(active_tab="login")
		else:
			messagebox.showerror("Error", "Failed to register.")

	def _reset_user_password(self, user_id: int, new_password: str):
		if not self.conn:
			return False
		pw_hash = hash_password(new_password.strip())
		return execute(self.conn, "UPDATE user SET password=%s WHERE user_id=%s", (pw_hash, user_id))

	# ===================== USER DASHBOARD =====================
	def create_user_dashboard(self):
		if not self.current_user:
			self.show_login()
			return
		self._clear_root()
		self._navbar()
		# hero section with logo instead of banner
		hero = ttk.Frame(self.root, padding=16)
		hero.pack(fill="x")
		hero_card = ttk.Frame(hero, style="Card.TFrame", padding=18)
		hero_card.pack(fill="x")

		top_row = ttk.Frame(hero_card)
		top_row.pack(fill="x")
		logo_path = get_or_create_logo()
		if logo_path and Image and os.path.exists(logo_path):
			try:
				img = Image.open(logo_path)
				img.thumbnail((140, 140), Image.Resampling.LANCZOS)
				self._dashboard_logo_imgtk = ImageTk.PhotoImage(img)
				logo_label = tk.Label(top_row, image=self._dashboard_logo_imgtk, bg=COLORS["card"], bd=0)
				logo_label.pack(side="left", padx=(0, 18))
			except Exception:
				tk.Label(top_row, text="🌟", font=("Segoe UI", 46), bg=COLORS["card"], fg=COLORS["accent"]).pack(side="left", padx=(0, 18))
		else:
			tk.Label(top_row, text="🌟", font=("Segoe UI", 46), bg=COLORS["card"], fg=COLORS["accent"]).pack(side="left", padx=(0, 18))

		title_block = ttk.Frame(top_row)
		title_block.pack(side="left", fill="y", expand=True)
		ttk.Label(title_block, text="Welcome back!", style="H1.TLabel").pack(anchor="w")
		ttk.Label(title_block, text="Share your latest stories and connect with friends.", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

		stats_row = ttk.Frame(hero_card)
		stats_row.pack(fill="x", pady=(14, 0))
		for label, icon in [
			("Create Posts", "📝"),
			("Engage with Friends", "🤝"),
			("Track Growth", "📈"),
		]:
			chip = ttk.Frame(stats_row, padding=(14, 10), style="Card.TFrame")
			chip.pack(side="left", padx=(0, 12))
			tk.Label(chip, text=icon, font=("Segoe UI", 20), bg=COLORS["card"]).pack()
			ttk.Label(chip, text=label, style="Muted.TLabel").pack()
		header = ttk.Frame(self.root, padding=(12, 0))
		header.pack(fill="x")
		ttk.Label(header, text="Home Feed", style="H1.TLabel").pack(side="left")
		RoundedButton(header, "➕ New Post", self.add_post, bg=COLORS["accent_alt"], hover_bg="#FF8A3D").pack(side="right", padx=6)

		_, _, feed = make_scrollable(self.root)
		self._render_feed(feed, all_posts=True)

	def _render_feed(self, container, all_posts: bool):
		for w in container.winfo_children():
			w.destroy()
		if all_posts:
			rows = fetch_all(self.conn,
				"SELECT p.post_id, p.user_id, u.username, p.content, p.created_at "
				"FROM post p JOIN user u ON u.user_id=p.user_id "
				"ORDER BY p.created_at DESC")
		else:
			rows = fetch_all(self.conn,
				"SELECT p.post_id, p.user_id, u.username, p.content, p.created_at "
				"FROM post p JOIN user u ON u.user_id=p.user_id "
				"WHERE p.user_id=%s ORDER BY p.created_at DESC", (self.current_user[0],))
		for (post_id, author_id, username, content, created_at) in rows:
			self._post_card(container, post_id, author_id, username, content, created_at)

	def _post_card(self, parent, post_id: int, author_id: int, username: str, content: str, created_at: Any):
		card = ttk.Frame(parent, style="Card.TFrame", padding=14)
		card.pack(fill="x", padx=16, pady=10)
		header = ttk.Frame(card)
		header.pack(fill="x")
		ttk.Label(header, text=f"@{username}", style="H2.TLabel").pack(side="left")
		ttk.Label(header, text=str(created_at), style="Muted.TLabel").pack(side="right")
		# image if exists
		img_map = load_image_map()
		img_path = img_map.get(str(post_id))
		if not img_path or not os.path.exists(img_path):
			# generate placeholder once
			ensure_assets_dir()
			img_path = os.path.join(ASSETS_DIR, f"post_{post_id}.png")
			if not os.path.exists(img_path):
				generate_placeholder_image(img_path, username)
			img_map[str(post_id)] = img_path
			save_image_map(img_map)
		if Image and os.path.exists(img_path):
			try:
				img = Image.open(img_path)
				img.thumbnail((900, 420))
				imgtk = ImageTk.PhotoImage(img)
				lbl = tk.Label(card, image=imgtk, bg=COLORS["card"])
				lbl.image = imgtk
				lbl.pack(fill="x", pady=(8,6))
			except Exception:
				pass
		ttk.Label(card, text=content, wraplength=800).pack(anchor="w", pady=6)
		# stats
		likes_row = fetch_one(self.conn, "SELECT COUNT(*) FROM postlike WHERE post_id=%s", (post_id,))
		comments_row = fetch_one(self.conn, "SELECT COUNT(*) FROM comment WHERE post_id=%s", (post_id,))
		likes = likes_row[0] if likes_row else 0
		comments = comments_row[0] if comments_row else 0
		stats = ttk.Frame(card); stats.pack(fill="x", pady=(4,6))
		ttk.Label(stats, text=f"❤ {likes}", style="Muted.TLabel", foreground="#E11D48").pack(side="left", padx=(0,10))
		ttk.Label(stats, text=f"💬 {comments}", style="Muted.TLabel", foreground="#2563EB").pack(side="left")
		# actions
		actions = ttk.Frame(card); actions.pack(fill="x")
		RoundedButton(actions, "❤ Like", lambda pid=post_id: self.like_post(pid), bg="#E11D48", hover_bg="#FB7185").pack(side="left", padx=4)
		RoundedButton(actions, "💬 Comment", lambda pid=post_id: self.add_comment(pid), bg="#2563EB", hover_bg="#60A5FA").pack(side="left", padx=4)
		if author_id != self.current_user[0]:
			RoundedButton(actions, "➕ Follow", lambda uid=author_id: self.follow_user(uid), bg="#10B981", hover_bg="#34D399").pack(side="left", padx=4)
		if author_id == self.current_user[0]:
			RoundedButton(actions, "✏ Edit", lambda pid=post_id, content=content: self.edit_post(pid, content), bg="#F59E0B", hover_bg="#FBBF24").pack(side="right", padx=4)
			RoundedButton(actions, "🗑 Delete", lambda pid=post_id: self.delete_post(pid), bg="#EF4444", hover_bg="#F87171").pack(side="right", padx=4)

	# ===================== USER ACTIONS =====================
	def add_post(self):
		if not self.current_user:
			return
		def on_submit(content: str, image_path: Optional[str]):
			if not content:
				messagebox.showwarning("Missing", "Please enter post content.")
				return
			uid = self.current_user[0]
			# Try procedure first
			ok = call_procedure(self.conn, "add_new_post", (uid, content))
			if not ok:
				# fallback direct insert
				ok = execute(self.conn, "INSERT INTO post (user_id, content, created_at) VALUES (%s,%s,NOW())", (uid, content))
			if not ok:
				messagebox.showerror("Error", "Failed to create post.")
				return
			# locate newest post id for this user
			row = fetch_one(self.conn, "SELECT post_id FROM post WHERE user_id=%s ORDER BY created_at DESC, post_id DESC LIMIT 1", (uid,))
			post_id = row[0] if row else None
			if post_id and image_path:
				try:
					ensure_assets_dir()
					dst = os.path.join(ASSETS_DIR, f"post_{post_id}" + os.path.splitext(image_path)[1].lower())
					# copy image
					with open(image_path, "rb") as src, open(dst, "wb") as out:
						out.write(src.read())
					img_map = load_image_map(); img_map[str(post_id)] = dst; save_image_map(img_map)
				except Exception as e:
					print("copy image error:", e, file=sys.stderr)
			messagebox.showinfo("Success", "Post published.")
			self.create_user_dashboard()
		AddPostDialog(self.root, on_submit)

	def edit_post(self, post_id: int, old_content: str):
		new_content = simpledialog.askstring("Edit Post", "Update content:", initialvalue=old_content)
		if not new_content:
			return
		ok = execute(self.conn, "UPDATE post SET content=%s WHERE post_id=%s AND user_id=%s", (new_content, post_id, self.current_user[0]))
		if ok:
			messagebox.showinfo("Updated", "Post updated.")
			self.create_user_dashboard()
		else:
			messagebox.showerror("Error", "Failed to update post.")

	def delete_post(self, post_id: int):
		if not messagebox.askyesno("Confirm", "Delete this post? Comments will be cascaded by trigger/policy."):
			return
		ok = execute(self.conn, "DELETE FROM post WHERE post_id=%s AND user_id=%s", (post_id, self.current_user[0]))
		if ok:
			messagebox.showinfo("Deleted", "Post removed.")
			self.create_user_dashboard()
		else:
			messagebox.showerror("Error", "Failed to delete post.")

	def like_post(self, post_id: int):
		if not self.current_user:
			return
		# naive toggle: if already liked, remove; else insert
		row = fetch_one(self.conn, "SELECT 1 FROM postlike WHERE user_id=%s AND post_id=%s", (self.current_user[0], post_id))
		if row:
			ok = execute(self.conn, "DELETE FROM postlike WHERE user_id=%s AND post_id=%s", (self.current_user[0], post_id))
			if ok:
				messagebox.showinfo("Unliked", "Like removed.")
		else:
			ok = execute(self.conn, "INSERT INTO postlike (user_id, post_id, liked_at) VALUES (%s,%s,NOW())", (self.current_user[0], post_id))
			if ok:
				# Trigger should add notification
				messagebox.showinfo("Liked", "You liked this post.")
		self.create_user_dashboard()

	def add_comment(self, post_id: int):
		text = simpledialog.askstring("Add Comment", "Your comment:")
		if not text:
			return
		ok = execute(self.conn, "INSERT INTO comment (post_id, user_id, comment_text, created_at) VALUES (%s,%s,%s,NOW())", (post_id, self.current_user[0], text))
		if ok:
			# Trigger should add notification
			messagebox.showinfo("Commented", "Comment added.")
			self.create_user_dashboard()
		else:
			messagebox.showerror("Error", "Failed to add comment.")

	def follow_user(self, target_user_id: int):
		if not self.current_user:
			return
		if target_user_id == self.current_user[0]:
			messagebox.showwarning("Not allowed", "You cannot follow yourself.")
			return
		# if already following -> unfollow, else follow via procedure
		row = fetch_one(self.conn, "SELECT 1 FROM follow WHERE follower_id=%s AND following_id=%s", (self.current_user[0], target_user_id))
		if row:
			ok = execute(self.conn, "DELETE FROM follow WHERE follower_id=%s AND following_id=%s", (self.current_user[0], target_user_id))
			if ok:
				messagebox.showinfo("Unfollowed", "You unfollowed the user.")
		else:
			ok = call_procedure(self.conn, "follow_user", (self.current_user[0], target_user_id))
			if not ok:
				# Fallback: direct insert if procedure missing
				ok = execute(self.conn, "INSERT INTO follow (follower_id, following_id, followed_at) VALUES (%s,%s,NOW())", (self.current_user[0], target_user_id))
			if ok:
				messagebox.showinfo("Followed", "You are now following this user.")
			else:
				messagebox.showerror("Error", "Failed to follow the user.")
		self.create_user_dashboard()

	# ===================== PROFILE =====================
	def show_profile(self):
		if not self.current_user:
			return
		self._clear_root()
		self._navbar()
		container = ttk.Frame(self.root, padding=12)
		container.pack(fill="both", expand=True)

		# Load profile details
		uid = self.current_user[0]
		user = fetch_one(self.conn, "SELECT username, email, bio, created_at FROM user WHERE user_id=%s", (uid,))
		username, email, bio, created_at = user if user else ("", "", "", "")
		metrics = self._get_user_metrics(uid)

		card = ttk.Frame(container, style="Card.TFrame", padding=16)
		card.pack(fill="x", padx=6, pady=6)
		ttk.Label(card, text=f"@{username}", style="H1.TLabel").pack(anchor="w")
		ttk.Label(card, text=email, style="Muted.TLabel").pack(anchor="w", pady=(0,8))
		ttk.Label(card, text=f"Bio: {bio or '—'}").pack(anchor="w")
		ttk.Label(card, text=f"Joined: {created_at}", style="Muted.TLabel").pack(anchor="w", pady=(0,8))
		stats = ttk.Frame(card); stats.pack(fill="x", pady=6)
		for label in [
			f"Posts: {metrics['posts']}",
			f"Likes: {metrics['likes']}",
			f"Followers: {metrics['followers']}",
			f"Following: {metrics['following']}",
			f"Engagement: {metrics['engagement']}%",
		]:
			ttk.Label(stats, text=label).pack(side="left", padx=(0,16))
		RoundedButton(card, "Edit Bio", self._edit_bio).pack(pady=6)

		# Engagement chart (pie showing engagement vs remaining)
		if Figure and FigureCanvasTkAgg:
			try:
				fig = Figure(figsize=(3.6, 2.0), dpi=100)
				ax = fig.add_subplot(111)
				val = max(0, min(100, float(metrics["engagement"] or 0)))
				ax.pie([val, 100 - val], colors=[COLORS["accent"], COLORS["border"]],
				       startangle=90, counterclock=False, wedgeprops={"linewidth": 0.5, "edgecolor": "white"})
				ax.legend(labels=[f"Engagement {val:.1f}%", ""], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)
				ax.axis("equal")
				canvas = FigureCanvasTkAgg(fig, master=card)
				canvas.draw()
				canvas.get_tk_widget().pack(pady=8, anchor="w")
			except Exception:
				pass

		ttk.Label(container, text="Your Posts", style="H2.TLabel").pack(anchor="w", padx=6, pady=(12,4))
		_, _, list_frame = make_scrollable(container)
		self._render_feed(list_frame, all_posts=False)

	# ===================== SEARCH USERS =====================
	def show_search(self):
		if not self.current_user:
			return
		self._clear_root()
		self._navbar()
		wrap = ttk.Frame(self.root, padding=12); wrap.pack(fill="both", expand=True)
		ttk.Label(wrap, text="Find People", style="H1.TLabel").pack(anchor="w")
		bar = ttk.Frame(wrap); bar.pack(fill="x", pady=(8,6))
		query_entry = ttk.Entry(bar, width=50)
		query_entry.pack(side="left", padx=(0,8), fill="x", expand=True)
		def do_search():
			self._render_search_results(results_frame, query_entry.get().strip())
		RoundedButton(bar, "Search", do_search).pack(side="left")
		_, _, results_frame = make_scrollable(wrap)
		# initial popular list (all except current, limited)
		self._render_search_results(results_frame, "")

	def _render_search_results(self, container, q: str):
		for w in container.winfo_children():
			w.destroy()
		params = ()
		if q:
			pattern = f"%{q}%"
			rows = fetch_all(self.conn, "SELECT user_id, username, email, bio FROM user WHERE (username LIKE %s OR email LIKE %s) AND user_id<>%s ORDER BY username LIMIT 100", (pattern, pattern, self.current_user[0]))
		else:
			rows = fetch_all(self.conn, "SELECT user_id, username, email, bio FROM user WHERE user_id<>%s ORDER BY created_at DESC LIMIT 50", (self.current_user[0],))
		if not rows:
			ttk.Label(container, text="No users found.", style="Muted.TLabel").pack(pady=16)
			return
		for uid, uname, email, bio in rows:
			card = ttk.Frame(container, style="Card.TFrame", padding=12)
			card.pack(fill="x", padx=8, pady=8)
			top = ttk.Frame(card); top.pack(fill="x")
			# avatar placeholder chip
			avatar = tk.Label(top, text=uname[:1].upper(), bg=COLORS["accent"], fg="white", width=2, height=1, font=("Segoe UI", 12, "bold"))
			avatar.pack(side="left", padx=(0,8))
			ttk.Label(top, text=f"@{uname}", style="H2.TLabel").pack(side="left")
			ttk.Label(top, text=email, style="Muted.TLabel").pack(side="right")
			if bio:
				ttk.Label(card, text=bio, wraplength=800).pack(anchor="w", pady=(6,0))
			# follow status
			row = fetch_one(self.conn, "SELECT 1 FROM follow WHERE follower_id=%s AND following_id=%s", (self.current_user[0], uid))
			btns = ttk.Frame(card); btns.pack(fill="x", pady=(6,0))
			if row:
				RoundedButton(btns, "Unfollow", lambda t=uid: self._search_unfollow_and_refresh(container, q, t)).pack(side="left", padx=4)
			else:
				RoundedButton(btns, "Follow", lambda t=uid: self._search_follow_and_refresh(container, q, t)).pack(side="left", padx=4)

	def _search_follow_and_refresh(self, container, q, target_uid):
		self.follow_user(target_uid)
		self._render_search_results(container, q)

	def _search_unfollow_and_refresh(self, container, q, target_uid):
		ok = execute(self.conn, "DELETE FROM follow WHERE follower_id=%s AND following_id=%s", (self.current_user[0], target_uid))
		if ok:
			messagebox.showinfo("Unfollowed", "You unfollowed the user.")
		self._render_search_results(container, q)

	def _edit_bio(self):
		new_bio = simpledialog.askstring("Edit Bio", "Update your bio:")
		if new_bio is None:
			return
		ok = call_procedure(self.conn, "update_user_bio", (self.current_user[0], new_bio))
		if not ok:
			ok = execute(self.conn, "UPDATE user SET bio=%s WHERE user_id=%s", (new_bio, self.current_user[0]))
		if ok:
			messagebox.showinfo("Saved", "Bio updated.")
			self.show_profile()

	# ===================== NOTIFICATIONS =====================
	def view_notifications(self):
		if not self.current_user:
			return
		self._clear_root()
		self._navbar()
		ttk.Label(self.root, text="Notifications", style="H1.TLabel").pack(anchor="w", padx=12, pady=(6, 0))
		_, _, container = make_scrollable(self.root)
		rows = fetch_all(self.conn, "SELECT notification_id, message, is_read, created_at FROM notification WHERE user_id=%s ORDER BY created_at DESC", (self.current_user[0],))
		if not rows:
			ttk.Label(container, text="No notifications yet.", style="Muted.TLabel").pack(pady=20)
		else:
			for (nid, msg, is_read, created_at) in rows:
				card = ttk.Frame(container, style="Card.TFrame", padding=12)
				card.pack(fill="x", padx=12, pady=8)
				top = ttk.Frame(card); top.pack(fill="x")
				ttk.Label(top, text=str(created_at), style="Muted.TLabel").pack(side="right")
				ttk.Label(card, text=msg).pack(anchor="w", pady=(6,0))
				if not is_read:
					RoundedButton(card, "Mark as read", lambda id=nid: self._mark_notification(id)).pack(pady=6)

	def _mark_notification(self, notification_id: int):
		ok = execute(self.conn, "UPDATE notification SET is_read=1 WHERE notification_id=%s AND user_id=%s", (notification_id, self.current_user[0]))
		if ok:
			self.view_notifications()

	# ===================== ADMIN DASHBOARD =====================
	def create_admin_dashboard(self):
		if not self.current_user or not self._is_admin():
			self.show_login()
			return
		self._clear_root()
		self._navbar()
		tabs = ttk.Notebook(self.root)
		tabs.pack(fill="both", expand=True, padx=8, pady=8)

		users_tab = ttk.Frame(tabs); posts_tab = ttk.Frame(tabs); analytics_tab = ttk.Frame(tabs)
		tabs.add(users_tab, text="Users"); tabs.add(posts_tab, text="Posts"); tabs.add(analytics_tab, text="Analytics")

		# Users table
		cols_u = ("user_id","username","email","bio","created_at")
		tv_users = ttk.Treeview(users_tab, columns=cols_u, show="headings", height=16)
		for c in cols_u: tv_users.heading(c, text=c); tv_users.column(c, width=160 if c!="bio" else 300, anchor="w")
		tv_users.pack(fill="both", expand=True, padx=8, pady=8)
		for row in fetch_all(self.conn, "SELECT user_id, username, email, bio, created_at FROM user ORDER BY user_id"):
			tv_users.insert("", "end", values=row)
		btns_u = ttk.Frame(users_tab); btns_u.pack(fill="x", padx=8, pady=(0,8))
		RoundedButton(btns_u, "Delete User", lambda: self._admin_delete_user(tv_users)).pack(side="left", padx=6)

		# Posts table
		cols_p = ("post_id","user_id","username","content","created_at")
		tv_posts = ttk.Treeview(posts_tab, columns=cols_p, show="headings", height=16)
		for c in cols_p: tv_posts.heading(c, text=c); tv_posts.column(c, width=160 if c not in ("content","username") else 260, anchor="w")
		tv_posts.pack(fill="both", expand=True, padx=8, pady=8)
		for row in fetch_all(self.conn, "SELECT p.post_id, p.user_id, u.username, p.content, p.created_at FROM post p JOIN user u ON u.user_id=p.user_id ORDER BY p.created_at DESC"):
			tv_posts.insert("", "end", values=row)
		btns_p = ttk.Frame(posts_tab); btns_p.pack(fill="x", padx=8, pady=(0,8))
		RoundedButton(btns_p, "Delete Post", lambda: self._admin_delete_post(tv_posts)).pack(side="left", padx=6)

		# Analytics
		a_container = ttk.Frame(analytics_tab, padding=12); a_container.pack(fill="both", expand=True)
		ttk.Label(a_container, text="Per-user metrics", style="H2.TLabel").pack(anchor="w")
		cols_a = ("user_id","username","posts","likes","followers","following","engagement_%")
		tv_a = ttk.Treeview(a_container, columns=cols_a, show="headings", height=16)
		for c in cols_a: tv_a.heading(c, text=c); tv_a.column(c, width=120, anchor="center")
		tv_a.pack(fill="both", expand=True, pady=8)
		users = fetch_all(self.conn, "SELECT user_id, username FROM user ORDER BY user_id")
		for uid, uname in users:
			stats = self._get_user_metrics(uid)
			tv_a.insert("", "end", values=(uid, uname, stats["posts"], stats["likes"], stats["followers"], stats["following"], stats["engagement"]))

		# Engagement chart across users (top 10 by engagement)
		if Figure and FigureCanvasTkAgg:
			try:
				top_rows = fetch_all(self.conn, "SELECT user_id, username FROM user ORDER BY user_id LIMIT 50")
				data = []
				for uid, uname in top_rows:
					er = self._get_user_metrics(uid)["engagement"]
					data.append((uname, float(er)))
				data.sort(key=lambda x: x[1], reverse=True)
				data = data[:10]
				if data:
					names = [n for n,_ in data]
					values = [v for _,v in data]
					fig = Figure(figsize=(5.5, 2.2), dpi=100)
					ax = fig.add_subplot(111)
					bars = ax.bar(names, values, color=COLORS["accent"])
					ax.set_title("Top Engagement Rates")
					ax.set_ylabel("%")
					ax.set_ylim(0, max(100, max(values)+10))
					for b, v in zip(bars, values):
						ax.text(b.get_x()+b.get_width()/2, v+1, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
					ax.tick_params(axis='x', rotation=30)
					canvas = FigureCanvasTkAgg(fig, master=a_container)
					canvas.draw()
					canvas.get_tk_widget().pack(fill="x", pady=8)
			except Exception:
				pass

	def _admin_delete_user(self, tv):
		sel = tv.selection()
		if not sel:
			return
		vals = tv.item(sel[0], "values")
		uid = int(vals[0])
		if not messagebox.askyesno("Confirm", f"Delete user #{uid}?"):
			return
		# Caution: in real systems, consider soft-delete
		ok = execute(self.conn, "DELETE FROM user WHERE user_id=%s", (uid,))
		if ok:
			messagebox.showinfo("Deleted", "User removed.")
			self.create_admin_dashboard()

	def _admin_delete_post(self, tv):
		sel = tv.selection()
		if not sel:
			return
		vals = tv.item(sel[0], "values")
		pid = int(vals[0])
		if not messagebox.askyesno("Confirm", f"Delete post #{pid}?"):
			return
		ok = execute(self.conn, "DELETE FROM post WHERE post_id=%s", (pid,))
		if ok:
			messagebox.showinfo("Deleted", "Post removed.")
			self.create_admin_dashboard()


# ===================== MAIN =====================

def main():
	root = tk.Tk()
	app = BlogifyApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()