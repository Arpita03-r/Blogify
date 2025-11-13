"""
Mini Instagram-Style Blog GUI Application
A complete Tkinter application simulating an Instagram-style blog interface
with posts, likes, comments, and user profiles.

Author: Generated for Harini's Blog
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# ==================== CONFIGURATION ====================

# Color scheme - Modern pastel colors
COLORS = {
    'bg_primary': '#F8F9FA',      # Light gray background
    'bg_secondary': '#FFFFFF',    # White for cards
    'accent': '#FF6B9D',          # Pink accent
    'accent_hover': '#FF8FB3',    # Lighter pink on hover
    'text_primary': '#2C3E50',    # Dark gray text
    'text_secondary': '#7F8C8D',  # Light gray text
    'border': '#E1E8ED',          # Light border
    'like': '#E74C3C',            # Red for likes
    'comment': '#3498DB',         # Blue for comments
    'button_bg': '#FF6B9D',       # Pink button background
    'button_text': '#FFFFFF',     # White button text
}

# Fonts
FONT_TITLE = ('Segoe UI', 18, 'bold')
FONT_HEADING = ('Segoe UI', 14, 'bold')
FONT_BODY = ('Segoe UI', 11)
FONT_SMALL = ('Segoe UI', 9)

# File paths
DATA_FILE = 'blog_data.json'
IMAGES_DIR = 'blog_images'

# ==================== DATA MANAGEMENT ====================

def ensure_images_directory():
    """Create images directory if it doesn't exist."""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

def load_data() -> Dict:
    """
    Load blog data from JSON file.
    Creates file with sample data if it doesn't exist.
    
    Returns:
        Dict containing posts, users, and other data
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            return create_default_data()
    else:
        return create_default_data()

def create_default_data() -> Dict:
    """
    Create default data structure with 3 sample posts.
    
    Returns:
        Dict with initial sample data
    """
    default_data = {
        'current_user': {
            'user_id': 1,
            'username': 'harini',
            'email': 'harini@example.com',
            'bio': 'Welcome to my blog! ✨ Sharing moments and thoughts.',
            'created_at': datetime.now().isoformat()
        },
        'posts': [
            {
                'post_id': 1,
                'user_id': 1,
                'username': 'harini',
                'content': 'Beautiful sunset at the beach! 🌅 #sunset #beach #nature',
                'image_path': None,  # Placeholder
                'likes': 42,
                'liked_by': [],
                'comments': [
                    {'user_id': 2, 'username': 'friend1', 'text': 'Amazing shot!', 'created_at': datetime.now().isoformat()},
                    {'user_id': 3, 'username': 'friend2', 'text': 'Love this! ❤️', 'created_at': datetime.now().isoformat()}
                ],
                'created_at': datetime.now().isoformat()
            },
            {
                'post_id': 2,
                'user_id': 1,
                'username': 'harini',
                'content': 'Coffee and coding ☕💻 Perfect morning vibes!',
                'image_path': None,
                'likes': 28,
                'liked_by': [],
                'comments': [
                    {'user_id': 2, 'username': 'friend1', 'text': 'Same here!', 'created_at': datetime.now().isoformat()}
                ],
                'created_at': datetime.now().isoformat()
            },
            {
                'post_id': 3,
                'user_id': 1,
                'username': 'harini',
                'content': 'New project coming soon! Stay tuned 🚀 #coding #project',
                'image_path': None,
                'likes': 35,
                'liked_by': [],
                'comments': [],
                'created_at': datetime.now().isoformat()
            }
        ],
        'users': [
            {
                'user_id': 1,
                'username': 'harini',
                'email': 'harini@example.com',
                'bio': 'Welcome to my blog! ✨ Sharing moments and thoughts.',
                'created_at': datetime.now().isoformat()
            }
        ],
        'notifications': []
    }
    save_data(default_data)
    return default_data

def save_data(data: Dict):
    """Save blog data to JSON file."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save data: {e}")

# ==================== UI COMPONENTS ====================

class RoundedButton(tk.Canvas):
    """Custom rounded button widget."""
    
    def __init__(self, parent, text, command, width=120, height=35, 
                 bg_color=COLORS['button_bg'], text_color=COLORS['button_text'],
                 hover_color=COLORS['accent_hover'], **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=COLORS['bg_primary'], **kwargs)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.width = width
        self.height = height
        
        # Create rounded rectangle
        self.rect_id = self.create_rounded_rect(5, 5, width-5, height-5, 
                                                radius=15, fill=bg_color, outline='')
        self.text_id = self.create_text(width//2, height//2, text=text,
                                       fill=text_color, font=FONT_BODY)
        
        # Bind events
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind_all('<Button-1>', lambda e: self._on_click(e) if self.winfo_containing(e.x_root, e.y_root) == self else None)
        
    def create_rounded_rect(self, x1, y1, x2, y2, radius=15, **kwargs):
        """Create a rounded rectangle on canvas."""
        points = []
        for x, y in [(x1+radius, y1), (x2-radius, y1), (x2, y1), (x2, y1+radius),
                     (x2, y2-radius), (x2, y2), (x2-radius, y2), (x1+radius, y2),
                     (x1, y2), (x1, y2-radius), (x1, y1+radius), (x1, y1)]:
            points.extend([x, y])
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_click(self, event):
        """Handle button click."""
        if self.command:
            self.command()
    
    def _on_enter(self, event):
        """Handle mouse enter - change color."""
        self.itemconfig(self.rect_id, fill=self.hover_color)
    
    def _on_leave(self, event):
        """Handle mouse leave - restore color."""
        self.itemconfig(self.rect_id, fill=self.bg_color)

class PostCard:
    """Represents a single post card in the feed."""
    
    def __init__(self, parent, post_data, app_instance):
        self.parent = parent
        self.post_data = post_data
        self.app = app_instance
        
        # Create card frame
        self.frame = tk.Frame(parent, bg=COLORS['bg_secondary'], 
                             relief='flat', bd=0)
        self.frame.pack(fill='x', padx=20, pady=15)
        
        # Add border effect
        border_frame = tk.Frame(self.frame, bg=COLORS['border'], height=1)
        border_frame.pack(fill='x', side='top')
        
        self._create_card()
    
    def _create_card(self):
        """Build the post card UI."""
        # Header with username
        header_frame = tk.Frame(self.frame, bg=COLORS['bg_secondary'])
        header_frame.pack(fill='x', padx=15, pady=10)
        
        username_label = tk.Label(header_frame, text=f"@{self.post_data['username']}",
                                 font=FONT_HEADING, bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_primary'])
        username_label.pack(side='left')
        
        # Image placeholder
        image_frame = tk.Frame(self.frame, bg=COLORS['border'], height=300)
        image_frame.pack(fill='x', padx=15, pady=5)
        
        if self.post_data.get('image_path') and os.path.exists(self.post_data['image_path']):
            try:
                img = Image.open(self.post_data['image_path'])
                img = img.resize((600, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(image_frame, image=photo, bg=COLORS['border'])
                img_label.image = photo  # Keep reference
                img_label.pack(fill='both', expand=True)
            except Exception as e:
                self._create_placeholder(image_frame)
        else:
            self._create_placeholder(image_frame)
        
        # Caption
        caption_frame = tk.Frame(self.frame, bg=COLORS['bg_secondary'])
        caption_frame.pack(fill='x', padx=15, pady=10)
        
        caption_text = tk.Text(caption_frame, wrap='word', height=3,
                              font=FONT_BODY, bg=COLORS['bg_secondary'],
                              fg=COLORS['text_primary'], relief='flat',
                              borderwidth=0, padx=0, pady=0)
        caption_text.insert('1.0', self.post_data['content'])
        caption_text.config(state='disabled')
        caption_text.pack(fill='x')
        
        # Action buttons frame
        actions_frame = tk.Frame(self.frame, bg=COLORS['bg_secondary'])
        actions_frame.pack(fill='x', padx=15, pady=10)
        
        # Like button
        like_frame = tk.Frame(actions_frame, bg=COLORS['bg_secondary'])
        like_frame.pack(side='left', padx=5)
        
        like_btn = tk.Button(like_frame, text=f"❤️ {self.post_data['likes']}",
                           font=FONT_BODY, bg=COLORS['bg_secondary'],
                           fg=COLORS['like'], relief='flat', cursor='hand2',
                           command=self._toggle_like)
        like_btn.pack(side='left')
        
        # Comment button
        comment_frame = tk.Frame(actions_frame, bg=COLORS['bg_secondary'])
        comment_frame.pack(side='left', padx=5)
        
        comment_count = len(self.post_data.get('comments', []))
        comment_btn = tk.Button(comment_frame, text=f"💬 {comment_count}",
                              font=FONT_BODY, bg=COLORS['bg_secondary'],
                              fg=COLORS['comment'], relief='flat', cursor='hand2',
                              command=self._show_comments)
        comment_btn.pack(side='left')
    
    def _create_placeholder(self, parent):
        """Create a placeholder image."""
        placeholder = tk.Label(parent, text="📷 Image Placeholder",
                             font=('Segoe UI', 16), bg=COLORS['border'],
                             fg=COLORS['text_secondary'], height=10)
        placeholder.pack(fill='both', expand=True)
    
    def _toggle_like(self):
        """Toggle like on post."""
        data = load_data()
        post_id = self.post_data['post_id']
        user_id = data['current_user']['user_id']
        
        # Find post in data
        for post in data['posts']:
            if post['post_id'] == post_id:
                if user_id in post.get('liked_by', []):
                    post['liked_by'].remove(user_id)
                    post['likes'] = max(0, post['likes'] - 1)
                else:
                    if 'liked_by' not in post:
                        post['liked_by'] = []
                    post['liked_by'].append(user_id)
                    post['likes'] += 1
                break
        
        save_data(data)
        self.app.refresh_feed()
    
    def _show_comments(self):
        """Open comments popup."""
        CommentsPopup(self.app.root, self.post_data, self.app)

# ==================== POPUP WINDOWS ====================

class AddPostPopup:
    """Popup window for adding a new post."""
    
    def __init__(self, parent, app_instance):
        self.app = app_instance
        self.image_path = None
        
        # Create popup window
        self.popup = tk.Toplevel(parent)
        self.popup.title("Add New Post")
        self.popup.geometry("500x600")
        self.popup.configure(bg=COLORS['bg_primary'])
        self.popup.resizable(False, False)
        
        # Center window
        self.popup.transient(parent)
        self.popup.grab_set()
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the add post UI."""
        # Title
        title_label = tk.Label(self.popup, text="Create New Post",
                              font=FONT_TITLE, bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=20)
        
        # Image selection
        img_frame = tk.Frame(self.popup, bg=COLORS['bg_primary'])
        img_frame.pack(pady=10, padx=20, fill='x')
        
        self.img_label = tk.Label(img_frame, text="No image selected",
                                 font=FONT_BODY, bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_secondary'], width=40, height=8)
        self.img_label.pack(fill='both', expand=True, padx=5, pady=5)
        
        select_btn = RoundedButton(img_frame, "Choose Image", 
                                  self._select_image, width=150, height=35)
        select_btn.pack(pady=10)
        
        # Caption
        caption_frame = tk.Frame(self.popup, bg=COLORS['bg_primary'])
        caption_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        caption_label = tk.Label(caption_frame, text="Caption:",
                                font=FONT_HEADING, bg=COLORS['bg_primary'],
                                fg=COLORS['text_primary'], anchor='w')
        caption_label.pack(fill='x', pady=(0, 5))
        
        self.caption_text = scrolledtext.ScrolledText(caption_frame, wrap='word',
                                                      height=8, font=FONT_BODY,
                                                      bg=COLORS['bg_secondary'],
                                                      fg=COLORS['text_primary'],
                                                      relief='flat', borderwidth=1)
        self.caption_text.pack(fill='both', expand=True)
        
        # Buttons
        btn_frame = tk.Frame(self.popup, bg=COLORS['bg_primary'])
        btn_frame.pack(pady=20)
        
        post_btn = RoundedButton(btn_frame, "Post", self._create_post,
                                width=120, height=40)
        post_btn.pack(side='left', padx=10)
        
        cancel_btn = RoundedButton(btn_frame, "Cancel", self._close,
                                  width=120, height=40,
                                  bg_color='#95A5A6', hover_color='#7F8C8D')
        cancel_btn.pack(side='left', padx=10)
    
    def _select_image(self):
        """Open file dialog to select image."""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if file_path:
            self.image_path = file_path
            try:
                img = Image.open(file_path)
                img = img.resize((400, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=photo, text='')
                self.img_label.image = photo
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def _create_post(self):
        """Create and save new post."""
        caption = self.caption_text.get('1.0', 'end-1c').strip()
        
        if not caption:
            messagebox.showwarning("Warning", "Please enter a caption!")
            return
        
        data = load_data()
        user = data['current_user']
        
        # Copy image to images directory if selected
        saved_image_path = None
        if self.image_path:
            ensure_images_directory()
            filename = os.path.basename(self.image_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_image_path = os.path.join(IMAGES_DIR, f"{timestamp}_{filename}")
            try:
                img = Image.open(self.image_path)
                img.save(saved_image_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")
                return
        
        # Create new post
        new_post = {
            'post_id': max([p['post_id'] for p in data['posts']], default=0) + 1,
            'user_id': user['user_id'],
            'username': user['username'],
            'content': caption,
            'image_path': saved_image_path,
            'likes': 0,
            'liked_by': [],
            'comments': [],
            'created_at': datetime.now().isoformat()
        }
        
        data['posts'].insert(0, new_post)  # Add to beginning
        save_data(data)
        
        messagebox.showinfo("Success", "Post created successfully!")
        self._close()
        self.app.refresh_feed()
    
    def _close(self):
        """Close popup."""
        self.popup.destroy()

class CommentsPopup:
    """Popup window for viewing and adding comments."""
    
    def __init__(self, parent, post_data, app_instance):
        self.post_data = post_data
        self.app = app_instance
        
        # Create popup window
        self.popup = tk.Toplevel(parent)
        self.popup.title("Comments")
        self.popup.geometry("500x500")
        self.popup.configure(bg=COLORS['bg_primary'])
        self.popup.resizable(False, False)
        
        # Center window
        self.popup.transient(parent)
        self.popup.grab_set()
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the comments UI."""
        # Title
        title_label = tk.Label(self.popup, text="Comments",
                              font=FONT_TITLE, bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=15)
        
        # Comments list (scrollable)
        comments_frame = tk.Frame(self.popup, bg=COLORS['bg_primary'])
        comments_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(comments_frame, bg=COLORS['bg_secondary'],
                          highlightthickness=0)
        scrollbar = ttk.Scrollbar(comments_frame, orient="vertical",
                                 command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_secondary'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Display existing comments
        comments = self.post_data.get('comments', [])
        if comments:
            for comment in comments:
                self._add_comment_display(scrollable_frame, comment)
        else:
            no_comments = tk.Label(scrollable_frame, text="No comments yet.",
                                  font=FONT_BODY, bg=COLORS['bg_secondary'],
                                  fg=COLORS['text_secondary'])
            no_comments.pack(pady=20)
        
        # Add comment section
        add_frame = tk.Frame(self.popup, bg=COLORS['bg_primary'])
        add_frame.pack(fill='x', padx=20, pady=10)
        
        self.comment_entry = tk.Text(add_frame, wrap='word', height=3,
                                    font=FONT_BODY, bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief='flat',
                                    borderwidth=1)
        self.comment_entry.pack(fill='x', pady=5)
        
        add_btn = RoundedButton(add_frame, "Add Comment", self._add_comment,
                               width=150, height=35)
        add_btn.pack(pady=5)
    
    def _add_comment_display(self, parent, comment):
        """Display a single comment."""
        comment_frame = tk.Frame(parent, bg=COLORS['bg_secondary'],
                                relief='flat', bd=1)
        comment_frame.pack(fill='x', padx=5, pady=5)
        
        username_label = tk.Label(comment_frame, text=f"@{comment['username']}",
                                 font=('Segoe UI', 10, 'bold'),
                                 bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_primary'], anchor='w')
        username_label.pack(fill='x', padx=10, pady=(5, 0))
        
        text_label = tk.Label(comment_frame, text=comment['text'],
                             font=FONT_SMALL, bg=COLORS['bg_secondary'],
                             fg=COLORS['text_secondary'], anchor='w',
                             wraplength=400, justify='left')
        text_label.pack(fill='x', padx=10, pady=(0, 5))
    
    def _add_comment(self):
        """Add a new comment."""
        comment_text = self.comment_entry.get('1.0', 'end-1c').strip()
        
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment!")
            return
        
        data = load_data()
        user = data['current_user']
        post_id = self.post_data['post_id']
        
        # Find post and add comment
        for post in data['posts']:
            if post['post_id'] == post_id:
                new_comment = {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'text': comment_text,
                    'created_at': datetime.now().isoformat()
                }
                if 'comments' not in post:
                    post['comments'] = []
                post['comments'].append(new_comment)
                break
        
        save_data(data)
        messagebox.showinfo("Success", "Comment added!")
        self.popup.destroy()
        self.app.refresh_feed()

class ProfilePopup:
    """Popup window for user profile."""
    
    def __init__(self, parent, app_instance):
        self.app = app_instance
        
        # Create popup window
        self.popup = tk.Toplevel(parent)
        self.popup.title("Profile")
        self.popup.geometry("400x500")
        self.popup.configure(bg=COLORS['bg_primary'])
        self.popup.resizable(False, False)
        
        # Center window
        self.popup.transient(parent)
        self.popup.grab_set()
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the profile UI."""
        data = load_data()
        user = data['current_user']
        
        # Title
        title_label = tk.Label(self.popup, text="Profile",
                              font=FONT_TITLE, bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=20)
        
        # Profile card
        profile_frame = tk.Frame(self.popup, bg=COLORS['bg_secondary'],
                                relief='flat', bd=1)
        profile_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Username
        username_label = tk.Label(profile_frame, text=f"@{user['username']}",
                                 font=FONT_TITLE, bg=COLORS['bg_secondary'],
                                 fg=COLORS['text_primary'])
        username_label.pack(pady=20)
        
        # Bio
        bio_label = tk.Label(profile_frame, text="Bio:",
                           font=FONT_HEADING, bg=COLORS['bg_secondary'],
                           fg=COLORS['text_primary'], anchor='w')
        bio_label.pack(fill='x', padx=20, pady=(10, 5))
        
        bio_text = tk.Label(profile_frame, text=user.get('bio', 'No bio set.'),
                          font=FONT_BODY, bg=COLORS['bg_secondary'],
                          fg=COLORS['text_secondary'], wraplength=300,
                          justify='left')
        bio_text.pack(fill='x', padx=20, pady=(0, 10))
        
        # Stats
        stats_frame = tk.Frame(profile_frame, bg=COLORS['bg_secondary'])
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        post_count = len([p for p in data['posts'] if p['user_id'] == user['user_id']])
        total_likes = sum([p['likes'] for p in data['posts'] if p['user_id'] == user['user_id']])
        
        posts_label = tk.Label(stats_frame, text=f"Posts: {post_count}",
                              font=FONT_BODY, bg=COLORS['bg_secondary'],
                              fg=COLORS['text_primary'])
        posts_label.pack(side='left', padx=10)
        
        likes_label = tk.Label(stats_frame, text=f"Total Likes: {total_likes}",
                              font=FONT_BODY, bg=COLORS['bg_secondary'],
                              fg=COLORS['text_primary'])
        likes_label.pack(side='left', padx=10)
        
        # Close button
        close_btn = RoundedButton(profile_frame, "Close", self._close,
                                 width=120, height=35)
        close_btn.pack(pady=20)
    
    def _close(self):
        """Close popup."""
        self.popup.destroy()

# ==================== MAIN APPLICATION ====================

class InstagramBlogApp:
    """Main application class for Instagram-style blog."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Harini's Blog")
        self.root.geometry("800x700")
        self.root.configure(bg=COLORS['bg_primary'])
        
        # Load data
        self.data = load_data()
        ensure_images_directory()
        
        # Create UI
        self._create_navbar()
        self._create_feed()
        
        # Initial feed load
        self.refresh_feed()
    
    def _create_navbar(self):
        """Create top navigation bar."""
        navbar = tk.Frame(self.root, bg=COLORS['bg_secondary'], height=60)
        navbar.pack(fill='x', side='top')
        navbar.pack_propagate(False)
        
        # Title
        title_label = tk.Label(navbar, text="Harini's Blog",
                              font=FONT_TITLE, bg=COLORS['bg_secondary'],
                              fg=COLORS['accent'])
        title_label.pack(side='left', padx=20, pady=15)
        
        # Navigation buttons
        nav_buttons = tk.Frame(navbar, bg=COLORS['bg_secondary'])
        nav_buttons.pack(side='right', padx=20, pady=15)
        
        home_btn = RoundedButton(nav_buttons, "🏠 Home", self._show_home,
                                width=100, height=30)
        home_btn.pack(side='left', padx=5)
        
        add_post_btn = RoundedButton(nav_buttons, "➕ Add Post",
                                     self._show_add_post, width=120, height=30)
        add_post_btn.pack(side='left', padx=5)
        
        profile_btn = RoundedButton(nav_buttons, "👤 Profile",
                                   self._show_profile, width=100, height=30)
        profile_btn.pack(side='left', padx=5)
    
    def _create_feed(self):
        """Create scrollable feed area."""
        # Main container
        feed_container = tk.Frame(self.root, bg=COLORS['bg_primary'])
        feed_container.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(feed_container, bg=COLORS['bg_primary'],
                               highlightthickness=0)
        scrollbar = ttk.Scrollbar(feed_container, orient="vertical",
                                 command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS['bg_primary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def refresh_feed(self):
        """Refresh the post feed."""
        # Clear existing posts
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Load fresh data
        self.data = load_data()
        
        # Create post cards
        posts = sorted(self.data['posts'], 
                      key=lambda x: x.get('created_at', ''),
                      reverse=True)  # Newest first
        
        if not posts:
            no_posts = tk.Label(self.scrollable_frame,
                              text="No posts yet. Create your first post!",
                              font=FONT_HEADING, bg=COLORS['bg_primary'],
                              fg=COLORS['text_secondary'])
            no_posts.pack(pady=50)
        else:
            for post in posts:
                PostCard(self.scrollable_frame, post, self)
        
        # Update canvas scroll region
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _show_home(self):
        """Show home feed."""
        self.refresh_feed()
    
    def _show_add_post(self):
        """Open add post popup."""
        AddPostPopup(self.root, self)
    
    def _show_profile(self):
        """Open profile popup."""
        ProfilePopup(self.root, self)

# ==================== MAIN ENTRY POINT ====================

def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = InstagramBlogApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

