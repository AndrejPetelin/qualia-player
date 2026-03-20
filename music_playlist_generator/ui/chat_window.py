"""Tkinter chat interface"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path
from typing import Callable, Optional

class ChatWindow:
    def __init__(self, 
                 on_send_message: Callable[[str], None],
                 on_rescan: Callable[[], None],
                 on_change_folder: Callable[[Path], None]):
        """
        Args:
            on_send_message: Callback when user sends a message
            on_rescan: Callback when user clicks rescan button
            on_change_folder: Callback when user selects new music folder
        """
        self.on_send_message = on_send_message
        self.on_rescan = on_rescan
        self.on_change_folder = on_change_folder
        
        self.root = tk.Tk()
        self.root.title("Music Playlist Generator")
        self.root.geometry("800x600")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout"""
        
        # Top toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.folder_label = ttk.Label(toolbar, text="Music Folder: Not set")
        self.folder_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="Change Folder", command=self._change_folder).pack(side=tk.LEFT, padx=5)
        
        self.rescan_btn = ttk.Button(toolbar, text="Rescan Library", command=self._rescan, state=tk.DISABLED)
        self.rescan_btn.pack(side=tk.LEFT, padx=5)
        
        self.track_count_label = ttk.Label(toolbar, text="Tracks: 0")
        self.track_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Arial", 10)
        )
        self.chat_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags for styling
        self.chat_display.tag_config("user", foreground="blue", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="green")
        self.chat_display.tag_config("system", foreground="gray", font=("Arial", 9, "italic"))
        
        # Input area
        input_frame = ttk.Frame(self.root)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.input_field = ttk.Entry(input_frame, font=("Arial", 10))
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side=tk.RIGHT)
    
    def _change_folder(self):
        """Let user select a new music folder"""
        folder = filedialog.askdirectory(title="Select Music Folder")
        if folder:
            self.on_change_folder(Path(folder))
    
    def _rescan(self):
        """Trigger library rescan"""
        self.on_rescan()
    
    def _send_message(self):
        """Send user message"""
        message = self.input_field.get().strip()
        if message:
            self.input_field.delete(0, tk.END)
            self.on_send_message(message)
    
    def add_message(self, sender: str, message: str):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        tag = "system"
        if sender == "You":
            tag = "user"
        elif sender == "Assistant":
            tag = "assistant"
        
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_folder_label(self, folder: Path):
        """Update the folder display"""
        self.folder_label.config(text=f"Music Folder: {folder}")
        self.rescan_btn.config(state=tk.NORMAL)
    
    def update_track_count(self, count: int):
        """Update the track count display"""
        self.track_count_label.config(text=f"Tracks: {count}")
    
    def show_rescan_notification(self):
        """Highlight the rescan button"""
        self.rescan_btn.config(text="⚠ Rescan Library (changes detected)")
    
    def clear_rescan_notification(self):
        """Clear rescan notification"""
        self.rescan_btn.config(text="Rescan Library")
    
    def run(self):
        """Start the UI event loop"""
        self.root.mainloop()
