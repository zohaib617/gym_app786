
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import time
import threading
import sqlite3

DB_PATH = 'gym.db'
DEVICE_IP = '192.168.10.11'
DEVICE_PORT = 4370

_last_checked = None  # Global to track last checked timestamp
stop_loop = False     # Global flag to stop attendance loop


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor


def get_members(cursor):
    cursor.execute("SELECT fingerprint_id, name FROM members")
    rows = cursor.fetchall()
    members = {int(fingerprint_id): name for fingerprint_id, name in rows}
    return members


def is_already_marked(cursor, fingerprint_id, date_str):
    cursor.execute("SELECT 1 FROM attendance WHERE fingerprint_id = ? AND date = ?", (fingerprint_id, date_str))
    return cursor.fetchone() is not None


def insert_attendance(cursor, fingerprint_id, name, date_str, time_str):
    cursor.execute("""
        INSERT INTO attendance (fingerprint_id, name, date, time)
        VALUES (?, ?, ?, ?)
    """, (fingerprint_id, name, date_str, time_str))


def show_gui_window(fingerprint_id):
    conn, cursor = connect_db()
    cursor.execute("SELECT member_id, name, balance, photo_path FROM members WHERE fingerprint_id = ?", (fingerprint_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return

    member_id, name, balance, photo_path = result

    window = tk.Toplevel()
    window.title("🎉 Member Info")
    window.geometry("700x400")
    window.configure(bg="#f5f5f5")

    main_frame = ttk.Frame(window, padding=20, relief="ridge", borderwidth=3)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)

    info_frame = ttk.Frame(main_frame, padding=20, relief="solid", borderwidth=2)
    info_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    name_label = ttk.Label(info_frame, text=f"🧑 Name: {name}", font=("Segoe UI", 14, "bold"))
    name_label.pack(anchor="w", pady=5)

    id_label = ttk.Label(info_frame, text=f"🆔 Member ID: {member_id}", font=("Segoe UI", 12))
    id_label.pack(anchor="w", pady=5)
    
    # Balance color logic
    if balance == 0:
        bal_color = "green"
    elif balance > 500:
        bal_color = "blue"
    else:
        bal_color = "black"

    bal_label = ttk.Label(info_frame, text=f"💰 Dua Amount: Rs. {balance}", font=("Segoe UI", 12), foreground=bal_color)
    bal_label.pack(anchor="w", pady=5)

    photo_frame = ttk.Frame(main_frame, padding=10)
    photo_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    try:
        photo_path = photo_path.replace("\\", "/")
        if os.path.exists(photo_path):
            img = Image.open(photo_path)
            img = img.resize((250, 320))
            photo = ImageTk.PhotoImage(img)

            photo_label = tk.Label(photo_frame, image=photo, borderwidth=2, relief="groove")
            photo_label.image = photo
            photo_label.pack()
        else:
            tk.Label(photo_frame, text="❌ Photo not found", fg="red", font=("Arial", 12)).pack()
    except Exception as e:
        tk.Label(photo_frame, text=f"❌ Error loading image: {e}", fg="red", font=("Arial", 10)).pack()


def check_new_attendance(last_checked):
    conn, cursor = connect_db()
    members = get_members(cursor)
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=5)

    try:
        conn_device = zk.connect()
        logs = conn_device.get_attendance()
        conn_device.disconnect()

        if not logs:
            return None

        logs = sorted(logs, key=lambda x: x.timestamp)

        for record in logs:
            ts = record.timestamp
            if last_checked is None or ts > last_checked:
                user_id = int(record.user_id)
                date_str = ts.strftime("%Y-%m-%d")
                time_str = ts.strftime("%H:%M:%S")

                if user_id in members:
                    name = members[user_id]

                    if not is_already_marked(cursor, user_id, date_str):
                        insert_attendance(cursor, user_id, name, date_str, time_str)
                        conn.commit()
                        return {
                            'fingerprint_id': user_id,
                            'name': name,
                            'date': date_str,
                            'time': time_str,
                            'timestamp': ts
                        }
    except Exception as e:
        print(f"Error in device connection: {e}")
        return None
    finally:
        conn.close()

    return None


def run_attendance_loop(log_widget):
    global _last_checked, stop_loop

    def log(msg):
        def inner():
            log_widget.insert("end", msg + "\n")
            log_widget.see("end")
        log_widget.after(0, inner)

    while not stop_loop:
        try:
            log("🔄 Checking attendance...")
            new_attendance = check_new_attendance(_last_checked)

            if new_attendance:
                _last_checked = new_attendance['timestamp']
                log(f"✅ New Attendance: {new_attendance['name']} at {new_attendance['time']} on {new_attendance['date']}")

                def show_window():
                    show_gui_window(new_attendance['fingerprint_id'])
                log_widget.after(0, show_window)

            else:
                log("ℹ️ No new attendance found.")

        except Exception as e:
            log(f"❌ Error in attendance loop: {e}")

        time.sleep(2)


def start_attendance_gui():
    global stop_loop
    stop_loop = False

    win = tk.Toplevel()
    win.title("🔄 Attendance Window")
    win.geometry("800x400")

    log_box = tk.Text(win, wrap="word", font=("Segoe UI", 11))
    log_box.pack(expand=True, fill="both", padx=10, pady=10)

    thread = threading.Thread(target=run_attendance_loop, args=(log_box,), daemon=True)
    thread.start()

    def on_close():
        global stop_loop
        stop_loop = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)