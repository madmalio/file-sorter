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

# --- CONSTANTS ---
# !!! IMPORTANT: Replace this URL with the raw URL to your own version.json file on GitHub !!!
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/madmalio/file-sorter/main/version.json"


class CustomMessageBox(customtkinter.CTkToplevel):
    """A custom messagebox that matches the app's theme."""
    def __init__(self, master, title="MessageBox", message="Message", on_close=None):
        super().__init__(master)
        self.on_close_callback = on_close

        self.title(title)
        self.geometry("400x150")
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        message_label = customtkinter.CTkLabel(main_frame, text=message, wraplength=350, justify="center")
        message_label.pack(expand=True, fill="both")

        ok_button = customtkinter.CTkButton(main_frame, text="OK", command=self._close_and_callback, width=100)
        ok_button.pack(pady=(10,0))
        
        self.after(50, self.lift)
        self.after(100, self.center_window)
        
    def _close_and_callback(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()

    def center_window(self):
        try:
            self.update_idletasks()
            width = self.winfo_width(); height = self.winfo_height()
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f'{width}x{height}+{x}+{y}')
        except Exception: pass

class CustomQuestionBox(customtkinter.CTkToplevel):
    """A custom question box with Yes/No buttons."""
    def __init__(self, master, title="Question", message="Message", on_yes=None, on_no=None):
        super().__init__(master)
        self.on_yes_callback = on_yes
        self.on_no_callback = on_no

        self.title(title); self.geometry("400x170")
        self.transient(master); self.grab_set()
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        message_label = customtkinter.CTkLabel(main_frame, text=message, wraplength=350, justify="center")
        message_label.pack(expand=True, fill="both")

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(10,0))

        yes_button = customtkinter.CTkButton(button_frame, text="Yes", command=self._yes_action, width=100)
        yes_button.pack(side="left", padx=10)
        no_button = customtkinter.CTkButton(button_frame, text="No", command=self._no_action, width=100)
        no_button.pack(side="left", padx=10)
        
        self.after(50, self.lift)
        self.after(100, self.center_window)

    def _yes_action(self):
        if self.on_yes_callback: self.on_yes_callback()
        self.destroy()

    def _no_action(self):
        if self.on_no_callback: self.on_no_callback()
        self.destroy()

    def center_window(self):
        try:
            self.update_idletasks()
            width = self.winfo_width(); height = self.winfo_height()
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f'{width}x{height}+{x}+{y}')
        except Exception: pass


class FileSorterApp(customtkinter.CTk):
    APP_VERSION = "1.2"
    
    def __init__(self):
        super().__init__()

        # --- State Variables ---
        self.config_file = "sorter_config.json"
        self.file_type_selector_window = None; self.settings_window = None; self.about_window = None
        self.checkbox_vars = {}; self.operation_mode_var = customtkinter.StringVar()

        self.load_and_apply_settings()

        self.title("Advanced File Sorter"); self.geometry("850x700"); self.minsize(800, 650)
        
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_rowconfigure(2, weight=1)

        title_frame = customtkinter.CTkFrame(self)
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        title_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(title_frame, text="Advanced File Sorter", font=customtkinter.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
        
        button_frame = customtkinter.CTkFrame(title_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")
        settings_button = customtkinter.CTkButton(button_frame, text="⚙", width=30, command=self.open_settings_window); settings_button.grid(row=0, column=0, padx=5)
        about_button = customtkinter.CTkButton(button_frame, text="?", width=30, command=self.open_about_window); about_button.grid(row=0, column=1, padx=(0,5))
        
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
        customtkinter.CTkLabel(options_frame, text="Date Sorting", font=customtkinter.CTkFont(weight="bold")).grid(row=1, column=0, padx=15, pady=(5, 15), sticky="w")
        current_year = datetime.now().year
        date_options = ["Disabled", f"Year/Month ({current_year}/JAN)", f"Year/Month/Day ({current_year}/JAN/05)", f"Year-Month ({current_year}-01)"]
        self.date_format_menu = customtkinter.CTkOptionMenu(options_frame, values=date_options); self.date_format_menu.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=(5, 15), sticky="w"); self.date_format_menu.set(date_options[1])
        customtkinter.CTkLabel(options_frame, text="Other", font=customtkinter.CTkFont(weight="bold")).grid(row=2, column=0, padx=15, pady=(5, 15), sticky="w")
        self.recursive_sort = customtkinter.CTkCheckBox(options_frame, text="Include subfolders (thorough sort)"); self.recursive_sort.grid(row=2, column=1, sticky="w")

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
        try: button_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
        except KeyError: button_fg_color = "#3a7ebf"
        if mode == "Move":
            self.move_button.configure(fg_color=button_fg_color, border_width=0)
            self.copy_button.configure(fg_color="transparent", border_width=1, border_color=button_fg_color)
        else:
            self.copy_button.configure(fg_color=button_fg_color, border_width=0)
            self.move_button.configure(fg_color="transparent", border_width=1, border_color=button_fg_color)

    def open_about_window(self):
        if self.about_window and self.about_window.winfo_exists(): self.about_window.focus(); return
        self.about_window = customtkinter.CTkToplevel(self)
        self.about_window.title("About"); self.about_window.geometry("400x250"); self.about_window.transient(self); self.about_window.grab_set()
        customtkinter.CTkLabel(self.about_window, text=f"Advanced File Sorter v{self.APP_VERSION}", font=customtkinter.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        customtkinter.CTkLabel(self.about_window, text="A utility to efficiently organize your files.", wraplength=350).pack(pady=5)
        customtkinter.CTkLabel(self.about_window, text="Built with Python and CustomTkinter.", font=customtkinter.CTkFont(slant="italic")).pack(pady=(10, 20))
        button_frame = customtkinter.CTkFrame(self.about_window, fg_color="transparent"); button_frame.pack(pady=10)
        customtkinter.CTkButton(button_frame, text="Check for Updates", command=self.check_for_updates).pack(side="left", padx=10)
        customtkinter.CTkButton(button_frame, text="Close", command=self.about_window.destroy).pack(side="left", padx=10)

    def check_for_updates(self):
        threading.Thread(target=self._perform_update_check, daemon=True).start()

    def _perform_update_check(self):
        # First, check if the URL is still a placeholder
        if "YOUR_USERNAME" in GITHUB_VERSION_URL:
            self.after(0, lambda: CustomMessageBox(self.about_window if self.about_window else self, 
                                                    title="Configuration Needed", 
                                                    message="The update check is not configured.\nPlease set the GITHUB_VERSION_URL in the script."))
            return
            
        try:
            response = requests.get(GITHUB_VERSION_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            latest_version = data['latest_version']
            
            # Simple version comparison
            if float(latest_version) > float(self.APP_VERSION):
                release_url = data['release_url']
                self.after(0, lambda: CustomQuestionBox(self.about_window if self.about_window else self, 
                                                        title="Update Available", 
                                                        message=f"A new version (v{latest_version}) is available!\nWould you like to go to the download page?",
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
            try: button_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
            except KeyError: button_fg_color = "#3a7ebf"
            if mode == "Move":
                settings_move_button.configure(fg_color=button_fg_color, border_width=0); settings_copy_button.configure(fg_color="transparent", border_width=1, border_color=button_fg_color)
            else:
                settings_copy_button.configure(fg_color=button_fg_color, border_width=0); settings_move_button.configure(fg_color="transparent", border_width=1, border_color=button_fg_color)
        settings_move_button.configure(command=lambda: (settings_op_mode_var.set("Move"), update_settings_op_buttons()))
        settings_copy_button.configure(command=lambda: (settings_op_mode_var.set("Copy"), update_settings_op_buttons()))
        update_settings_op_buttons()
        subfolders_check = customtkinter.CTkCheckBox(self.settings_window, text="Enable 'Include subfolders' by default")
        if self.settings.get("default_subfolders", True): subfolders_check.select()
        subfolders_check.pack(pady=(20,10))
        button_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent"); button_frame.pack(pady=(20, 10), fill="x", padx=20)
        def save_and_close():
            new_settings = {"theme": theme_menu.get(), "color_theme": color_theme_menu.get(), "default_operation": settings_op_mode_var.get(), "default_subfolders": bool(subfolders_check.get())}
            self.save_settings(new_settings)
            CustomMessageBox(self, title="Settings Saved", message="Please restart the application for all changes to take full effect.", on_close=self.settings_window.destroy)
        def reset_to_defaults():
            defaults = self.get_default_settings()
            theme_menu.set(defaults["theme"]); color_theme_menu.set(defaults["color_theme"]); settings_op_mode_var.set(defaults["default_operation"])
            if defaults["default_subfolders"]: subfolders_check.select()
            else: subfolders_check.deselect()
            update_settings_op_buttons()
        customtkinter.CTkButton(button_frame, text="Save & Close", command=save_and_close, font=customtkinter.CTkFont(weight="bold")).pack(side="right")
        customtkinter.CTkButton(button_frame, text="Reset", command=reset_to_defaults, fg_color="gray").pack(side="left")

    def open_file_type_selector(self):
        if self.file_type_selector_window and self.file_type_selector_window.winfo_exists(): self.file_type_selector_window.focus(); return
        self.file_type_selector_window = customtkinter.CTkToplevel(self); self.file_type_selector_window.title("Select File Types"); self.file_type_selector_window.geometry("500x450"); self.file_type_selector_window.transient(self); self.file_type_selector_window.grab_set()
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
        filename = os.path.basename(source_path); target_base = dest_folder; date_format = self.date_format_menu.get()
        if date_format != "Disabled":
            try:
                ctime = os.path.getctime(source_path); dt = datetime.fromtimestamp(ctime)
                if "Year/Month/Day" in date_format: parts = [str(dt.year), dt.strftime('%b').upper(), f"{dt.day:02d}"]
                elif "Year/Month" in date_format: parts = [str(dt.year), dt.strftime('%b').upper()]
                else: parts = [f"{dt.year}-{dt.month:02d}"]
                target_base = os.path.join(dest_folder, *parts)
            except Exception as e: self.log(f"Warning: Could not get date for {filename}: {e}.")
        final_dest = os.path.join(target_base, filename)
        log_prefix = "[DRY RUN] " if dry_run else ""; op_verb = "Would copy" if self.operation_mode_var.get() == "Copy" else "Would move"
        if not dry_run:
            os.makedirs(target_base, exist_ok=True); counter = 1
            while os.path.exists(final_dest):
                name, ext = os.path.splitext(filename); final_dest = os.path.join(target_base, f"{name}_{counter}{ext}"); counter += 1
            if self.operation_mode_var.get() == "Copy": shutil.copy2(source_path, final_dest); op_verb = "Copied"
            else: shutil.move(source_path, final_dest); op_verb = "Moved"
        self.log(f"{log_prefix}{op_verb}: {filename} -> {final_dest}")

    def sort_files(self, dry_run=False):
        dest = self.dest_entry.get(); moved = 0; mode = self.operation_mode_var.get()
        self.log(f"--- Starting {'Dry Run' if dry_run else f'{mode} Operation'} ---"); self.log(f"Origin: {self.origin_entry.get()}"); self.log(f"Destination: {dest}"); self.log(f"File types: {self.file_types_entry.get()}"); self.log(f"Date format: {self.date_format_menu.get()}"); self.log(f"Include subfolders: {'Yes' if self.recursive_sort.get() else 'No'}"); self.log("-" * 20)
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
    app = FileSorterApp()
    app.mainloop()

