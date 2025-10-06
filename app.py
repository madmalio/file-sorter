import multiprocessing
import os
import shutil
import json
import customtkinter
from tkinter import filedialog
from datetime import datetime
import threading
import sys
import requests
import webbrowser
import ctypes
from PIL import Image
import subprocess

# --- CONSTANTS ---
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/madmalio/sorteo/main/version.json"

# --- HELPER FUNCTION ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class CustomMessageBox(customtkinter.CTkToplevel):
    """A custom messagebox that matches the app's theme."""
    def __init__(self, master, title="MessageBox", message="Message", on_close=None):
        super().__init__(master)
        self.on_close_callback = on_close

        self.title(title)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        message_label = customtkinter.CTkLabel(main_frame, text=message, wraplength=350, justify="center")
        message_label.pack(expand=True, fill="both", padx=10, pady=10)

        ok_button = customtkinter.CTkButton(main_frame, text="OK", command=self._close_and_callback, width=100)
        ok_button.pack(pady=(10,0))
        
        self.update_idletasks()
        width = 350; height = 150
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.lift()
        self.focus_force()
        self.grab_set()
        
    def _close_and_callback(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class CustomQuestionBox(customtkinter.CTkToplevel):
    """A custom question box with Yes/No buttons."""
    def __init__(self, master, title="Question", message="Message", on_yes=None, on_no=None):
        super().__init__(master)
        self.on_yes_callback = on_yes
        self.on_no_callback = on_no

        self.title(title)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        message_label = customtkinter.CTkLabel(main_frame, text=message, wraplength=350, justify="center")
        message_label.pack(expand=True, fill="both", padx=10, pady=10)

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(10,0))

        yes_button = customtkinter.CTkButton(button_frame, text="Yes", command=self._yes_action, width=100)
        yes_button.pack(side="left", padx=10)
        no_button = customtkinter.CTkButton(button_frame, text="No", command=self._no_action, width=100)
        no_button.pack(side="left", padx=10)
        
        self.update_idletasks()
        width = 400; height = 170
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        self.lift()
        self.focus_force()
        self.grab_set()

    def _yes_action(self):
        if self.on_yes_callback: self.on_yes_callback()
        self.destroy()

    def _no_action(self):
        if self.on_no_callback: self.on_no_callback()
        self.destroy()


class FileSorterApp(customtkinter.CTk):
    APP_VERSION = "1.0.0"
    
    def __init__(self):
        super().__init__()

        # --- Set Application Icon ---
        try:
            icon_path = resource_path("sorteo.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting icon: {e}")

        # --- State Variables ---
        self.config_file = "sorter_config.json"
        self.file_type_selector_window = None; self.settings_window = None; self.about_window = None
        self.checkbox_vars = {}; self.operation_mode_var = customtkinter.StringVar()

        self.load_and_apply_settings()

        self.title("Sorteo"); self.geometry("850x750"); self.minsize(800, 700)

        # --- Fix for dark title bar on Windows ---
        self._apply_dark_title_bar()
        
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_rowconfigure(2, weight=1)

        title_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        title_frame.grid_columnconfigure(0, weight=1)

        try:
            logo_image = customtkinter.CTkImage(
                light_image=Image.open(resource_path("images/sorteo_logo_lightmode.png")),
                dark_image=Image.open(resource_path("images/sorteo_logo_darkmode.png")),
                size=(122, 32)
            )
            logo_label = customtkinter.CTkLabel(title_frame, image=logo_image, text="")
            logo_label.grid(row=0, column=0, sticky="w", padx=10)
        except Exception as e:
            print(f"Error loading logo: {e}")
            customtkinter.CTkLabel(title_frame, text="Sorteo", font=customtkinter.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
        
        button_frame = customtkinter.CTkFrame(title_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")
        settings_button = customtkinter.CTkButton(button_frame, text="⚙", width=30, command=self.open_settings_window)
        settings_button.grid(row=0, column=0, padx=5)
        about_button = customtkinter.CTkButton(button_frame, text="?", width=30, command=self.open_about_window)
        about_button.grid(row=0, column=1, padx=(0,5))
        
        path_frame = customtkinter.CTkFrame(main_frame); path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10)); path_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(path_frame, text="Origin Folder", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        self.origin_entry = customtkinter.CTkEntry(path_frame, placeholder_text="Select a source folder..."); self.origin_entry.grid(row=0, column=1, padx=(0, 10), pady=(15, 5), sticky="ew")
        customtkinter.CTkButton(path_frame, text="Browse...", width=100, command=self.browse_origin).grid(row=0, column=2, padx=(0, 15), pady=(15, 5))
        customtkinter.CTkLabel(path_frame, text="Destination Folder", font=customtkinter.CTkFont(weight="bold")).grid(row=1, column=0, padx=15, pady=(5, 15), sticky="w")
        self.dest_entry = customtkinter.CTkEntry(path_frame, placeholder_text="Select a destination folder..."); self.dest_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 15), sticky="ew")
        customtkinter.CTkButton(path_frame, text="Browse...", width=100, command=self.browse_dest).grid(row=1, column=2, padx=(0, 15), pady=(5, 15))

        options_frame = customtkinter.CTkFrame(main_frame); options_frame.grid(row=1, column=0, sticky="ew", pady=10); options_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(options_frame, text="File Types", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.file_types_entry = customtkinter.CTkEntry(options_frame, placeholder_text="e.g., pdf, docx, jpg"); self.file_types_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=15); self.file_types_entry.insert(0, "pdf, docx, xlsx, jpg, png, txt")
        customtkinter.CTkButton(options_frame, text="Select...", width=100, command=self.open_file_type_selector).grid(row=0, column=2, padx=(0, 15), pady=15)
        
        customtkinter.CTkLabel(options_frame, text="Sorting Structure", font=customtkinter.CTkFont(weight="bold")).grid(row=1, column=0, padx=15, pady=(5, 15), sticky="w")
        structure_options = ["Year/Month", "Year/Month/Day", "File Type", "File Type/Year/Month", "Topic/Year/Month", "Custom..."]
        
        def on_structure_change(choice):
            if "Topic" in choice or "Custom" in choice:
                self.topic_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0,5), padx=10)
            else:
                self.topic_frame.grid_forget()
            
            if "Custom" in choice:
                self.custom_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0,5), padx=10)
            else:
                self.custom_frame.grid_forget()

        self.sorting_structure_menu = customtkinter.CTkOptionMenu(options_frame, values=structure_options, command=on_structure_change)
        self.sorting_structure_menu.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=(5, 15), sticky="w")
        self.sorting_structure_menu.set(structure_options[0])

        self.topic_frame = customtkinter.CTkFrame(options_frame, fg_color="transparent")
        customtkinter.CTkLabel(self.topic_frame, text="Topic Name", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 15), sticky="w")
        self.topic_entry = customtkinter.CTkEntry(self.topic_frame, placeholder_text="e.g., Project_Alpha")
        self.topic_entry.grid(row=0, column=1, sticky="ew", padx=15, pady=(5,15))
        self.topic_frame.grid_columnconfigure(1, weight=1)
        
        self.custom_frame = customtkinter.CTkFrame(options_frame, fg_color="transparent")
        customtkinter.CTkLabel(self.custom_frame, text="Custom Structure", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 5), sticky="w")
        self.custom_entry = customtkinter.CTkEntry(self.custom_frame, placeholder_text="{topic}/{type}/{year}-{month}")
        self.custom_entry.grid(row=0, column=1, sticky="ew", padx=15, pady=(5,5))
        self.custom_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.custom_frame, text="Use: {type} {topic} {year} {month} {day}", text_color="gray", font=customtkinter.CTkFont(size=10)).grid(row=1, column=1, sticky="w", padx=15, pady=(0,10))

        customtkinter.CTkLabel(options_frame, text="Other", font=customtkinter.CTkFont(weight="bold")).grid(row=4, column=0, padx=15, pady=(5, 15), sticky="w")
        self.recursive_sort = customtkinter.CTkCheckBox(options_frame, text="Include subfolders (thorough sort)"); self.recursive_sort.grid(row=4, column=1, sticky="w")

        self.log_area = customtkinter.CTkTextbox(main_frame, state="disabled", font=("Consolas", 12)); self.log_area.grid(row=2, column=0, sticky="nsew", pady=10)

        action_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent"); action_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0)); action_frame.grid_columnconfigure(1, weight=1)
        self.progress_bar = customtkinter.CTkProgressBar(action_frame); self.progress_bar.set(0); self.progress_bar.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        op_button_frame = customtkinter.CTkFrame(action_frame, fg_color="transparent"); op_button_frame.grid(row=1, column=0, padx=(0,10), sticky="w")
        self.move_button = customtkinter.CTkButton(op_button_frame, text="Move", width=70, command=lambda: self.set_operation_mode("Move"), corner_radius=5); self.move_button.pack(side="left")
        self.copy_button = customtkinter.CTkButton(op_button_frame, text="Copy", width=70, command=lambda: self.set_operation_mode("Copy"), corner_radius=5); self.copy_button.pack(side="left", padx=(5,0))
        action_frame.grid_columnconfigure(1, weight=1)
        self.dry_run_button = customtkinter.CTkButton(action_frame, text="Dry Run (Preview)", command=lambda: self.start_sorting_thread(dry_run=True)); self.dry_run_button.grid(row=1, column=2, padx=(0,10))
        self.sort_button = customtkinter.CTkButton(action_frame, text="Start Sorting", command=self.start_sorting_thread, font=customtkinter.CTkFont(size=14, weight="bold")); self.sort_button.grid(row=1, column=3, sticky="e")
        
        self.apply_settings_to_ui(self.settings)

    def _restart_app(self):
        """Restarts the current application by replacing the current process."""
        self.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _apply_dark_title_bar(self):
        """Forces the window's title bar to be dark on Windows."""
        try:
            if sys.platform == "win32":
                self.update()
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                value = 2
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(value)), ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

    def get_default_settings(self):
        return {"theme": "System", "color_theme": "blue", "default_operation": "Move", "default_subfolders": True}

    def load_and_apply_settings(self):
        try:
            with open(self.config_file, 'r') as f: self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): self.settings = self.get_default_settings()
        customtkinter.set_appearance_mode(self.settings.get("theme", "System"))
        valid_themes = ["blue", "green", "dark-blue"]; color_theme = self.settings.get("color_theme", "blue")
        if color_theme not in valid_themes: color_theme = "blue"
        customtkinter.set_default_color_theme(color_theme)

    def apply_settings_to_ui(self, settings):
        self.set_operation_mode(settings.get("default_operation", "Move"));
        if settings.get("default_subfolders", True): self.recursive_sort.select()
        else: self.recursive_sort.deselect()

    def save_settings(self, new_settings):
        with open(self.config_file, 'w') as f: json.dump(new_settings, f, indent=4)
        self.settings = new_settings

    def set_operation_mode(self, mode): self.operation_mode_var.set(mode); self.update_operation_button_styles()
    def update_operation_button_styles(self):
        mode = self.operation_mode_var.get()
        inactive_color = "transparent" if customtkinter.get_appearance_mode() == "Dark" else "#C9C9C9"
        try: 
            button_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
            border_color = button_fg_color
        except KeyError: 
            button_fg_color = "#3a7ebf"
            border_color = button_fg_color

        if mode == "Move":
            self.move_button.configure(fg_color=button_fg_color, border_width=0)
            self.copy_button.configure(fg_color=inactive_color, border_width=1, border_color=border_color)
        else:
            self.copy_button.configure(fg_color=button_fg_color, border_width=0)
            self.move_button.configure(fg_color=inactive_color, border_width=1, border_color=border_color)

    def open_about_window(self):
        if self.about_window and self.about_window.winfo_exists(): self.about_window.focus(); return
        self.about_window = customtkinter.CTkToplevel(self)
        self.about_window.title("About"); self.about_window.geometry("400x320"); self.about_window.transient(self); self.about_window.grab_set()
        
        content_frame = customtkinter.CTkFrame(self.about_window, fg_color="transparent")
        content_frame.pack(pady=20, padx=20, fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(content_frame, text=f"Sorteo v{self.APP_VERSION}", font=customtkinter.CTkFont(size=16, weight="bold")).pack(fill="x")
        customtkinter.CTkLabel(content_frame, text="A utility to efficiently organize your files.", wraplength=350).pack(pady=5, fill="x")
        
        customtkinter.CTkLabel(content_frame, text="Created by: madmalio", wraplength=350).pack(pady=(10, 5), fill="x")
        
        repo_link = "https://github.com/madmalio/sorteo"
        link_label = customtkinter.CTkLabel(content_frame, text="View Source on GitHub", text_color="#6A8EDD", cursor="hand2")
        link_label.pack()
        link_label.bind("<Button-1>", lambda e: webbrowser.open(repo_link))
        
        # Spacer
        customtkinter.CTkLabel(content_frame, text="").pack(expand=True)

        customtkinter.CTkLabel(content_frame, text="Built with Python and CustomTkinter.", font=customtkinter.CTkFont(size=10)).pack(pady=(10, 0))

        button_frame = customtkinter.CTkFrame(content_frame, fg_color="transparent"); button_frame.pack(pady=(15,0), side="bottom")
        customtkinter.CTkButton(button_frame, text="Check for Updates", command=self.check_for_updates).pack(side="left", padx=10)
        customtkinter.CTkButton(button_frame, text="Close", command=self.about_window.destroy).pack(side="left", padx=10)

    def check_for_updates(self):
        threading.Thread(target=self._perform_update_check, daemon=True).start()

    def _perform_update_check(self):
        if "YOUR_USERNAME" in GITHUB_VERSION_URL:
            self.after(0, lambda: CustomMessageBox(self.about_window if self.about_window else self, 
                                                    title="Configuration Needed", 
                                                    message="The update check is not configured.\nPlease set the GITHUB_VERSION_URL in the script."))
            return
            
        try:
            response = requests.get(GITHUB_VERSION_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            latest_version_str = data['latest_version']
            release_url = data['release_url']
            
            current_parts = [int(p) for p in self.APP_VERSION.split('.')]
            latest_parts = [int(p) for p in latest_version_str.split('.')]

            while len(current_parts) < len(latest_parts): current_parts.append(0)
            while len(latest_parts) < len(current_parts): latest_parts.append(0)

            if latest_parts > current_parts:
                self.after(0, lambda: CustomQuestionBox(self.about_window if self.about_window else self, 
                                                        title="Update Available", 
                                                        message=f"A new version (v{latest_version_str}) is available!\nWould you like to go to the download page?",
                                                        on_yes=lambda: webbrowser.open(release_url)))
            else:
                self.after(0, lambda: CustomMessageBox(self.about_window if self.about_window else self, title="Up to Date", message=f"You are running the latest version (v{self.APP_VERSION})."))
        except Exception as e:
            self.after(0, lambda: CustomMessageBox(self.about_window if self.about_window else self, title="Update Error", message=f"Could not check for updates.\nPlease check your internet connection."))

    def open_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists(): self.settings_window.focus(); return
        self.settings_window = customtkinter.CTkToplevel(self)
        self.settings_window.title("Settings"); self.settings_window.geometry("400x420"); self.settings_window.transient(self); self.settings_window.grab_set()
        customtkinter.CTkLabel(self.settings_window, text="Appearance Theme", font=customtkinter.CTkFont(weight="bold")).pack(pady=(20, 5))
        theme_menu = customtkinter.CTkOptionMenu(self.settings_window, values=["System", "Light", "Dark"]); theme_menu.set(self.settings.get("theme", "System")); theme_menu.pack()
        customtkinter.CTkLabel(self.settings_window, text="Accent Color", font=customtkinter.CTkFont(weight="bold")).pack(pady=(20, 5))
        valid_themes = ["blue", "green", "dark-blue"]; saved_color_theme = self.settings.get("color_theme", "blue")
        if saved_color_theme not in valid_themes: saved_color_theme = "blue"
        color_theme_menu = customtkinter.CTkOptionMenu(self.settings_window, values=valid_themes); color_theme_menu.set(saved_color_theme); color_theme_menu.pack()
        customtkinter.CTkLabel(self.settings_window, text="Default Operation Mode", font=customtkinter.CTkFont(weight="bold")).pack(pady=(20, 5))
        settings_op_mode_var = customtkinter.StringVar(value=self.settings.get("default_operation", "Move"))
        op_mode_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent"); op_mode_frame.pack()
        settings_move_button = customtkinter.CTkButton(op_mode_frame, text="Move", width=70, corner_radius=5); settings_move_button.pack(side="left")
        settings_copy_button = customtkinter.CTkButton(op_mode_frame, text="Copy", width=70, corner_radius=5); settings_copy_button.pack(side="left", padx=(5,0))
        
        def update_settings_op_buttons():
            mode = settings_op_mode_var.get()
            inactive_color = "transparent" if customtkinter.get_appearance_mode() == "Dark" else "#C9C9C9"
            try: 
                button_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
                border_color = button_fg_color
            except KeyError: 
                button_fg_color = "#3a7ebf"
                border_color = button_fg_color
            
            if mode == "Move":
                settings_move_button.configure(fg_color=button_fg_color, border_width=0)
                settings_copy_button.configure(fg_color=inactive_color, border_width=1, border_color=border_color)
            else:
                settings_copy_button.configure(fg_color=button_fg_color, border_width=0)
                settings_move_button.configure(fg_color=inactive_color, border_width=1, border_color=border_color)
                
        settings_move_button.configure(command=lambda: (settings_op_mode_var.set("Move"), update_settings_op_buttons()))
        settings_copy_button.configure(command=lambda: (settings_op_mode_var.set("Copy"), update_settings_op_buttons()))
        update_settings_op_buttons()
        subfolders_check = customtkinter.CTkCheckBox(self.settings_window, text="Enable 'Include subfolders' by default")
        if self.settings.get("default_subfolders", True): subfolders_check.select()
        subfolders_check.pack(pady=(20,10))
        button_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent"); button_frame.pack(pady=(20, 10), fill="x", padx=20)
        
        def save_and_close():
            old_theme = self.settings.get("theme", "System")
            old_color_theme = self.settings.get("color_theme", "blue")
            old_operation_mode = self.settings.get("default_operation", "Move")
            old_subfolders = self.settings.get("default_subfolders", True)

            new_theme = theme_menu.get()
            new_color_theme = color_theme_menu.get()
            new_operation_mode = settings_op_mode_var.get()
            new_subfolders = bool(subfolders_check.get())

            theme_changed = new_theme != old_theme
            
            if theme_changed:
                customtkinter.set_appearance_mode(new_theme)
                self.update_operation_button_styles()

            new_settings = {
                "theme": new_theme, "color_theme": new_color_theme, 
                "default_operation": new_operation_mode, "default_subfolders": new_subfolders
            }
            self.save_settings(new_settings)

            restart_needed = (new_color_theme != old_color_theme or
                              new_operation_mode != old_operation_mode or
                              new_subfolders != old_subfolders)

            if restart_needed:
                def show_restart_dialog():
                    message = "Some settings require a restart to apply. Would you like to restart Sorteo now?"
                    if theme_changed:
                        message = "Appearance mode updated.\n" + message
                    
                    def on_yes_action():
                        self.settings_window.destroy()
                        self._restart_app()

                    def on_no_action():
                        self.settings_window.destroy()

                    CustomQuestionBox(self.settings_window, 
                                      title="Restart Required", 
                                      message=message, 
                                      on_yes=on_yes_action, 
                                      on_no=on_no_action)
                
                self.after(50, show_restart_dialog)
            else:
                self.settings_window.destroy()
        
        def reset_to_defaults():
            defaults = self.get_default_settings()
            theme_menu.set(defaults["theme"])
            color_theme_menu.set(defaults["color_theme"])
            settings_op_mode_var.set(defaults["default_operation"])
            if defaults["default_subfolders"]:
                subfolders_check.select()
            else:
                subfolders_check.deselect()
            update_settings_op_buttons()
            
        customtkinter.CTkButton(button_frame, text="Save & Close", command=save_and_close, font=customtkinter.CTkFont(weight="bold")).pack(side="right")
        customtkinter.CTkButton(button_frame, text="Reset", command=reset_to_defaults, fg_color="gray").pack(side="left")

    def open_file_type_selector(self):
        if self.file_type_selector_window and self.file_type_selector_window.winfo_exists(): self.file_type_selector_window.focus(); return
        self.file_type_selector_window = customtkinter.CTkToplevel(self)
        self.file_type_selector_window.title("Select File Types"); self.file_type_selector_window.geometry("500x450"); self.file_type_selector_window.transient(self); self.file_type_selector_window.grab_set()
        current_selection = [ft.strip().lower() for ft in self.file_types_entry.get().split(',') if ft.strip()]
        scrollable_frame = customtkinter.CTkScrollableFrame(self.file_type_selector_window, label_text="Available File Types"); scrollable_frame.pack(expand=True, fill="both", padx=15, pady=(15,0))
        all_file_types = { "Documents": ["pdf", "docx", "xlsx", "pptx", "txt", "csv", "rtf"], "Images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff", "heic"], "Audio": ["mp3", "wav", "aac", "flac", "m4a"], "Video": ["mp4", "mov", "avi", "mkv", "wmv"], "Archives": ["zip", "rar", "7z", "tar", "gz"],}
        self.checkbox_vars.clear()
        for category, types in all_file_types.items():
            customtkinter.CTkLabel(scrollable_frame, text=category, font=customtkinter.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 2))
            for file_type in types:
                var = customtkinter.StringVar(value="on" if file_type in current_selection else "off"); cb = customtkinter.CTkCheckBox(scrollable_frame, text=file_type, variable=var, onvalue="on", offvalue="off"); cb.pack(anchor="w", padx=10); self.checkbox_vars[file_type] = var
        button_frame = customtkinter.CTkFrame(self.file_type_selector_window, fg_color="transparent"); button_frame.pack(pady=15)
        customtkinter.CTkButton(button_frame, text="Select All", command=lambda: [var.set("on") for var in self.checkbox_vars.values()]).pack(side="left", padx=5)
        customtkinter.CTkButton(button_frame, text="Clear All", command=lambda: [var.set("off") for var in self.checkbox_vars.values()]).pack(side="left", padx=5)
        customtkinter.CTkButton(button_frame, text="Apply", command=self.update_selected_file_types, font=customtkinter.CTkFont(weight="bold")).pack(side="left", padx=5)

    def update_selected_file_types(self):
        selected = [ft for ft, var in self.checkbox_vars.items() if var.get() == "on"]; self.file_types_entry.delete(0, "end"); self.file_types_entry.insert(0, ", ".join(selected))
        if self.file_type_selector_window: self.file_type_selector_window.destroy(); self.file_type_selector_window = None

    def browse_origin(self): path = filedialog.askdirectory(); self.origin_entry.delete(0, "end"); self.origin_entry.insert(0, path)
    def browse_dest(self): path = filedialog.askdirectory(); self.dest_entry.delete(0, "end"); self.dest_entry.insert(0, path)
    def log(self, message): self.log_area.configure(state="normal"); self.log_area.insert("end", message + "\n"); self.log_area.see("end"); self.log_area.configure(state="disabled"); self.update_idletasks()

    def start_sorting_thread(self, dry_run=False):
        origin = self.origin_entry.get(); dest = self.dest_entry.get(); types = self.file_types_entry.get()
        if not all([origin, dest, types]): CustomMessageBox(self, title="Error", message="Please select origin, destination, and at least one file type."); return
        if not os.path.isdir(origin): CustomMessageBox(self, title="Error", message="Origin folder does not exist."); return
        
        structure = self.sorting_structure_menu.get()
        if ("Topic" in structure or ("Custom" in structure and "{topic}" in self.custom_entry.get())) and not self.topic_entry.get():
            CustomMessageBox(self, title="Error", message="Please enter a Topic Name for this structure.")
            return
        if "Custom" in structure and not self.custom_entry.get():
            CustomMessageBox(self, title="Error", message="Please enter a Custom Structure pattern.")
            return

        self.sort_button.configure(state="disabled"); self.dry_run_button.configure(state="disabled")
        self.log_area.configure(state="normal"); self.log_area.delete('1.0', "end"); self.log_area.configure(state="disabled")
        self.progress_bar.set(0); threading.Thread(target=self.sort_files, args=(dry_run,), daemon=True).start()
    
    def get_file_list(self):
        origin = self.origin_entry.get(); dest = self.dest_entry.get()
        types = [ft.strip().lower() for ft in self.file_types_entry.get().split(',') if ft.strip()]; file_list = []
        if self.recursive_sort.get():
            for dirpath, _, filenames in os.walk(origin):
                if dest and os.path.commonpath([dirpath, dest]) == dest: continue
                for filename in filenames:
                    if any(filename.lower().endswith(f".{ext}") for ext in types): file_list.append(os.path.join(dirpath, filename))
        else:
            for item in os.listdir(origin):
                path = os.path.join(origin, item)
                if os.path.isfile(path) and any(item.lower().endswith(f".{ext}") for ext in types): file_list.append(path)
        return file_list

    def process_file(self, source_path, dest_folder, dry_run=False):
        filename = os.path.basename(source_path)
        structure = self.sorting_structure_menu.get()
        
        if structure == "Custom...":
            pattern = self.custom_entry.get()
            sub_path = pattern
            try:
                dt = datetime.fromtimestamp(os.path.getctime(source_path))
                sub_path = sub_path.replace("{year}", str(dt.year))
                sub_path = sub_path.replace("{month}", dt.strftime('%b').upper())
                sub_path = sub_path.replace("{day}", f"{dt.day:02d}")
            except Exception as e:
                self.log(f"Warning: Could not get date for {filename}: {e}.")

            _, ext = os.path.splitext(filename)
            file_type = ext[1:].lower() if ext else "other"
            sub_path = sub_path.replace("{type}", file_type)

            topic = self.topic_entry.get().strip()
            sub_path = sub_path.replace("{topic}", topic)
            
            sub_path = sub_path.replace("\\", "/")
            path_parts = [part for part in sub_path.split("/") if part]

        else: # Handle predefined structures
            path_parts = []
            _, ext = os.path.splitext(filename)
            file_ext = ext[1:].lower() if ext else "other"

            if "Topic" in structure:
                topic_name = self.topic_entry.get().strip()
                if topic_name: path_parts.append(topic_name)
            
            if "File Type" in structure:
                path_parts.append(file_ext)

            if "Year" in structure or "Month" in structure or "Day" in structure:
                try:
                    ctime = os.path.getctime(source_path)
                    dt = datetime.fromtimestamp(ctime)
                    if "Year" in structure: path_parts.append(str(dt.year))
                    if "Month" in structure: path_parts.append(dt.strftime('%b').upper())
                    if "Day" in structure: path_parts.append(f"{dt.day:02d}")
                except Exception as e: 
                    self.log(f"Warning: Could not get date for {filename}: {e}.")
        
        target_base = os.path.join(dest_folder, *path_parts)
        final_dest = os.path.join(target_base, filename)
        
        log_prefix = "[DRY RUN] " if dry_run else ""
        op_verb = "Would copy" if self.operation_mode_var.get() == "Copy" else "Would move"
        if not dry_run:
            os.makedirs(target_base, exist_ok=True); counter = 1
            while os.path.exists(final_dest):
                name, ext = os.path.splitext(filename); final_dest = os.path.join(target_base, f"{name}_{counter}{ext}"); counter += 1
            if self.operation_mode_var.get() == "Copy": shutil.copy2(source_path, final_dest); op_verb = "Copied"
            else: shutil.move(source_path, final_dest); op_verb = "Moved"
        self.log(f"{log_prefix}{op_verb}: {filename} -> {final_dest}")

    def sort_files(self, dry_run=False):
        dest = self.dest_entry.get(); moved = 0; mode = self.operation_mode_var.get()
        self.log(f"--- Starting {'Dry Run' if dry_run else f'{mode} Operation'} ---")
        self.log(f"Origin: {self.origin_entry.get()}")
        self.log(f"Destination: {dest}")
        self.log(f"File types: {self.file_types_entry.get()}")
        
        structure = self.sorting_structure_menu.get()
        log_structure = self.custom_entry.get() if structure == "Custom..." else structure
        self.log(f"Structure: {log_structure}")

        self.log(f"Include subfolders: {'Yes' if self.recursive_sort.get() else 'No'}")
        self.log("-" * 20)
        try:
            files = self.get_file_list(); total = len(files)
            if total == 0: self.log("No matching files found to process.")
            for i, path in enumerate(files):
                self.process_file(path, dest, dry_run); moved += 1
                self.after(0, lambda p=(i + 1) / total: self.progress_bar.set(p))
        except Exception as e: self.log(f"ERROR: An unexpected error occurred: {e}"); CustomMessageBox(self, title="Error", message=f"An unexpected error occurred:\n{e}")
        finally:
            self.log(f"\n{'Dry run complete!' if dry_run else 'Operation complete!'} Processed {moved} files.")
            self.after(0, lambda: (self.sort_button.configure(state="normal"), self.dry_run_button.configure(state="normal")))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = FileSorterApp()
    app.mainloop()