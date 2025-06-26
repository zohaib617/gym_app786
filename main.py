import win32com.client
import base64

import threading

import random
from atten import start_attendance_gui 
from exe import open_member_search
from financial_report import open_financial_report
import shutil
from payment import open_payment_window
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import qrcode
import sqlite3
import datetime
from tkcalendar import DateEntry
import os
import sys
from datetime import datetime


selected_gym_id = None

# --- Create folders ---


# --- SQLite connection and tables ---
conn = sqlite3.connect("gym.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS fingerprint_templates (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gym_id TEXT,
    filename TEXT,
    saved_at TEXT
)
''')
conn.commit()


cursor.execute('''
CREATE TABLE IF NOT EXISTS email_config (
    gym_id TEXT PRIMARY KEY,
    sender_email TEXT,
    sender_password TEXT
)
''')
conn.commit()


cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        gym_id TEXT,
        member_id INTEGER,
        amount TEXT,
        payment_method TEXT,
        added_by_id INTEGER,
        added_by_name TEXT,
        entry_type TEXT,
        custom_date TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')


cursor.execute('''CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER ,
    gym_id TEXT,
    name TEXT,
    mobile TEXT UNIQUE,
    cnic TEXT,
    address TEXT,
    timing TEXT,
    entry_type text,
    admission_fees TEXT,
    email Text,
    monthly_fees TEXT,
    discount TEXT,
    after_discount TEXT,
    paid_fees TEXT,
    balance INTEGER,
    join_date TEXT,
    photo_path TEXT

    

)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
    fingerprint_id INTEGER ,
    gym_id TEXT,
    name TEXT,
    date TEXT,
    time TEXT
)''')


cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    member_id INTEGER,
    mobile Text,
    member_name TEXT,
    admission_fees Text,
    monthly_fees TEXT,
    join_date TEXT,
    email Text,
    balance TEXT,
    logs_time TEXT,
    Discount Text,
    entry_type TEXT,
    payment_id Text,
    payment text
)
''')

conn.commit()

# --- Functions ---

# --- Function to change theme ---



username = ""
role = ""

if os.path.exists("session.txt"):
    with open("session.txt", "r") as f:
        session = f.read().strip().split(",")
        if len(session) == 3:
            username, role, selected_gym_id = session  # ✅ gym ID include




from datetime import datetime

def insert_monthly_negative_entries():
    today = datetime.now().date()
    current_month = today.month
    current_year = today.year

    print(f"\n📅 System Date: {today.strftime('%d-%m-%Y')} | Month: {current_month}, Year: {current_year}")

    # 👇 Step 1: Get all members who have paid fees (safely match 'paid fees' with spaces/cases)
    cursor.execute("""
        SELECT DISTINCT member_id FROM payments
        WHERE REPLACE(LOWER(entry_type), ' ', '') = 'paidfees'
    """)
    members = cursor.fetchall()
    print(f"🔍 Found {len(members)} unique members with 'paid fees'")

    for (member_id,) in members:
        try:
            # 👇 Step 2: Get last paid fees custom_date for this member
            cursor.execute("""
                SELECT custom_date FROM payments
                WHERE member_id = ? AND REPLACE(LOWER(entry_type), ' ', '') = 'paidfees'
                ORDER BY payment_id DESC LIMIT 1
            """, (member_id,))
            result = cursor.fetchone()

            if result:
                last_paid_str = result[0]
                last_paid_date = datetime.strptime(last_paid_str, "%d-%m-%Y").date()
                days_since_last_paid = (today - last_paid_date).days

                print(f"\n➡ Member ID: {member_id}")
                print(f"📆 Last Paid Date: {last_paid_str} ({days_since_last_paid} days ago)")

                if days_since_last_paid >= 30:
                    # 👇 Step 3: Check if any payment exists this month for this member
                    cursor.execute("""
                        SELECT 1 FROM payments
                        WHERE member_id = ?
                        AND substr(custom_date, 4, 2) = ?
                        AND substr(custom_date, 7, 4) = ?
                    """, (member_id, f"{current_month:02}", str(current_year)))
                    payment_this_month = cursor.fetchone()

                    print(f"💰 Payment this month? {'✅' if payment_this_month else '❌'}")

                    if not payment_this_month:
                        # 👇 Step 4: Check if a "Monthly" negative entry already exists
                        cursor.execute("""
                            SELECT 1 FROM payments
                            WHERE member_id = ?
                            AND entry_type = 'Monthly'
                            AND payment_method = 'no'
                            AND substr(custom_date, 4, 2) = ?
                            AND substr(custom_date, 7, 4) = ?
                        """, (member_id, f"{current_month:02}", str(current_year)))
                        negative_exists = cursor.fetchone()

                        if not negative_exists:
                            cursor.execute("""
                                INSERT INTO payments (
                                    gym_id,
                                    member_id,
                                    amount,
                                    payment_method,
                                    added_by_id,
                                    added_by_name,
                                    entry_type,
                                    custom_date,
                                    timestamp
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (
                                selected_gym_id,
                                member_id,
                                "0",
                                "no",
                                "System",
                                "System",
                                "Monthly",
                                today.strftime("%d-%m-%Y")
                            ))
                            conn.commit()
                            print(f"✅ Negative entry inserted for Member ID {member_id}")
                        else:
                            print("⚠️ Negative entry already exists. Skipping.")
                    else:
                        print("✔️ Payment already done this month. Skipping.")
                else:
                    print("📆 Less than 30 days since last paid. Skipping.")

        except Exception as e:
            print(f"❌ Error for Member ID {member_id}: {e}")




def open_email_config_window():
    if not selected_gym_id:
        messagebox.showerror("No Gym ID", "Please select Gym ID first.")
        return

    win = tk.Toplevel(root)
    win.title("✉️ Email Config")
    win.geometry("400x300")

    conn_local = sqlite3.connect("gym.db")
    cursor_local = conn_local.cursor()

    email_var = tk.StringVar()
    pass_var = tk.StringVar()

    cursor_local.execute("SELECT sender_email, sender_password FROM email_config WHERE gym_id = ?", (selected_gym_id,))
    row = cursor_local.fetchone()
    if row:
        email_var.set(row[0])
        pass_var.set(row[1])

    tk.Label(win, text=f"Gym ID: {selected_gym_id}", font=("Arial", 12, "bold")).pack(pady=10)
    tk.Label(win, text="Sender Email:", font=("Arial", 12)).pack()
    tk.Entry(win, textvariable=email_var, font=("Arial", 12), width=40).pack()

    tk.Label(win, text="App Password:", font=("Arial", 12)).pack(pady=5)
    tk.Entry(win, textvariable=pass_var, font=("Arial", 12), width=40, show="*").pack()

    def save_email():
        cursor_local.execute("REPLACE INTO email_config (gym_id, sender_email, sender_password) VALUES (?, ?, ?)",
                             (selected_gym_id, email_var.get().strip(), pass_var.get().strip()))
        conn_local.commit()
        messagebox.showinfo("Saved", "Email settings saved.")
        win.destroy()

    def remove_email():
        cursor_local.execute("DELETE FROM email_config WHERE gym_id = ?", (selected_gym_id,))
        conn_local.commit()
        email_var.set("")
        pass_var.set("")
        messagebox.showinfo("Removed", "Email settings removed.")

    tk.Button(win, text="💾 Save", font=("Arial", 12), command=save_email).pack(pady=10)
    tk.Button(win, text="❌ Remove", font=("Arial", 12), command=remove_email).pack()

    win.protocol("WM_DELETE_WINDOW", lambda: (conn_local.close(), win.destroy()))




def change_theme(theme_name):
    colors = {
        "Light": {
            "bg": "#fdfdfd",
            "fg": "#333333",
            "menu_bg": "#f0f0f0",
            "button_bg": "#e6e6e6",
            "button_hover": "#d0d0d0",
            "entry_bg": "#ffffff"
        },
        "Dark": {
            "bg": "#2c2f33",
            "fg": "#ffffff",
            "menu_bg": "#23272a",
            "button_bg": "#3a3f44",
            "button_hover": "#4f545c",
            "entry_bg": "#40444b"
        },
        "Blue": {
            "bg": "#dbeeff",
            "fg": "#0f1c2e",
            "menu_bg": "#c4e0ff",
            "button_bg": "#a6d4ff",
            "button_hover": "#8ac8ff",
            "entry_bg": "#ffffff"
        },
        "Green": {
            "bg": "#e9f7ef",
            "fg": "#1b4d3e",
            "menu_bg": "#d4f4e3",
            "button_bg": "#b8e6d1",
            "button_hover": "#9edcc0",
            "entry_bg": "#ffffff"
        },
    }

    selected = colors.get(theme_name, colors["Light"])

    # Root background
    root.configure(bg=selected["bg"])
    main_frame.configure(style="Main.TFrame")
    content_frame.configure(style="Main.TFrame")
    menu_frame.configure(bg=selected["menu_bg"])  # menu is tk.Frame

    # Frames & Labels
    style.configure("Main.TFrame", background=selected["bg"])
    style.configure("TLabel", background=selected["bg"], foreground=selected["fg"])
    
    # Entry fields
    style.configure("TEntry",
        fieldbackground=selected["entry_bg"],
        foreground=selected["fg"],
        bordercolor=selected["fg"]
    )

    # Main buttons
    style.configure("TButton",
        background=selected["bg"],
        foreground=selected["fg"],
        borderwidth=0,
        padding=6
    )

    # Sidebar buttons
    style.configure("Sidebar.TButton",
        background=selected["button_bg"],
        foreground=selected["fg"],
        font=("Arial", 11),
        padding=8,
        relief="flat"
    )
    style.map("Sidebar.TButton",
        background=[("active", selected["button_hover"])],
        foreground=[("disabled", "#a0a0a0")]
    )

    # Optionally update user info box bg:
    user_info_frame.configure(bg=selected["menu_bg"])
    icon_label.configure(bg=selected["menu_bg"])
    text_label.configure(bg=selected["menu_bg"])

def open_finger():
    insert_monthly_negative_entries()
    subprocess.Popen(["Enrollment.exe"])



# --- Settings window ---
def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("⚙️ Settings")
    settings_win.geometry("350x300")
    settings_win.configure(bg="#f0f2f5")
    settings_win.resizable(False, False)

    # Frame for styling
    frame = tk.Frame(settings_win, bg="white", bd=2, relief="groove")
    frame.place(relx=0.5, rely=0.5, anchor="center", width=300, height=230)

    # Header
    tk.Label(
        frame,
        text="⚙️ Settings",
        font=("Segoe UI", 16, "bold"),
        bg="white",
        fg="#333"
    ).pack(pady=(15, 10))

    # Theme selection
    tk.Label(
        frame,
        text="🎨 Select Theme:",
        font=("Segoe UI", 11),
        bg="white"
    ).pack()

    theme_var = tk.StringVar()
    theme_dropdown = ttk.Combobox(
        frame,
        textvariable=theme_var,
        state="readonly",
        font=("Segoe UI", 10)
    )
    theme_dropdown["values"] = ("Light", "Dark", "Blue", "Green")
    theme_dropdown.current(0)
    theme_dropdown.pack(pady=5)

    def apply_theme():
        change_theme(theme_var.get())
        settings_win.destroy()

    # Buttons
    ttk.Button(frame, text="✅ Apply Theme", command=apply_theme).pack(pady=10)
    ttk.Button(frame, text="📧 Configure Email", command=open_email_config_window).pack()

    # Rounded corners look (optional)
    style = ttk.Style()
    style.configure("TButton", font=("Segoe UI", 10))



def logout():
    # Delete session file
    try:
        os.remove("session.txt")
    except FileNotFoundError:
        pass

    messagebox.showinfo("Logout", "You have been logged out.")
    root.destroy()  # Close main window

    # Open login window again
    subprocess.Popen(["login.exe"])


import smtplib
import random
from email.message import EmailMessage

def send_otp_to_email(gym_id, receiver_email):
    otp = str(random.randint(100000, 999999))

    import sqlite3
    conn = sqlite3.connect("gym.db")
    cursor = conn.cursor()

    cursor.execute("SELECT sender_email, sender_password FROM email_config WHERE gym_id = ?", (gym_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("No email config found for gym:", gym_id)
        return None

    sender_email, sender_password = row

    message = EmailMessage()
    message.set_content(f"Your OTP for password reset is: {otp}")
    message["Subject"] = "Password Reset OTP"
    message["From"] = sender_email
    message["To"] = receiver_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(message)
        return otp
    except Exception as e:
        print("Email send error:", e)
        return None




def open_register_window():
    register_win = tk.Toplevel(root)
    register_win.title("📝 Register User")
    register_win.geometry("400x450")
    register_win.resizable(False, False)
    register_win.configure(bg="#f4f4f4")

    # Variables
    new_username = tk.StringVar()
    new_password = tk.StringVar()
    new_email = tk.StringVar()
    new_role = tk.StringVar(value="Staff")

    # --- Style ---
    form_frame = ttk.Frame(register_win, padding=20)
    form_frame.pack(expand=True)

    ttk.Label(form_frame, text="👤 Create New Account", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    # Username
    ttk.Label(form_frame, text="Username:", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(form_frame, textvariable=new_username, width=30).grid(row=1, column=1, pady=5)

    # Email
    ttk.Label(form_frame, text="Email:", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(form_frame, textvariable=new_email, width=30).grid(row=2, column=1, pady=5)

    # Password
    ttk.Label(form_frame, text="Password:", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(form_frame, textvariable=new_password, show="*", width=30).grid(row=3, column=1, pady=5)

    # Role
    ttk.Label(form_frame, text="Select Role:", font=("Segoe UI", 11)).grid(row=4, column=0, sticky="e", padx=10, pady=5)
    ttk.Combobox(form_frame, textvariable=new_role, values=["Staff"], state="readonly", width=28).grid(row=4, column=1, pady=5)

    # Register function
    def register():
        if not new_username.get().strip() or not new_password.get().strip() or not new_email.get().strip():
            messagebox.showerror("❌ Error", "All fields are required!")
            return

        try:
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                           (new_username.get().strip(), new_password.get().strip(), new_email.get().strip(), new_role.get()))
            conn.commit()
            messagebox.showinfo("✅ Success", "User Registered Successfully!")
            register_win.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("❌ Error", "Username or Email already exists!")

    # Register button
    ttk.Button(form_frame, text="✅ Register", style="Sidebar.TButton", command=register).grid(row=5, column=0, columnspan=2, pady=10)

    # --- Optional Reset Password Button ---
    def open_reset():
        register_win.destroy()
        open_reset_password_window()

    ttk.Button(form_frame, text="🔁 Reset Password", command=open_reset).grid(row=6, column=0, columnspan=2, pady=10)
def open_reset_password_window():
    reset_win = tk.Toplevel(root)
    reset_win.title("🔐 Reset Password with OTP")
    reset_win.geometry("400x400")
    reset_win.configure(bg="#f4f4f4")

    email_var = tk.StringVar()
    otp_var = tk.StringVar()
    new_pass_var = tk.StringVar()
    generated_otp = None

    frame = ttk.Frame(reset_win, padding=20)
    frame.pack(expand=True)

    ttk.Label(frame, text="Email:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="e", pady=10)
    ttk.Entry(frame, textvariable=email_var, width=30).grid(row=0, column=1, pady=10)

    def send_otp():
        nonlocal generated_otp
        email = email_var.get().strip()
        if not email:
            messagebox.showerror("❌ Error", "Please enter your email.")
            return

        # Fetch gym_id from session.txt
        try:
            with open("session.txt", "r") as f:
                _, _, gym_id = f.read().strip().split(",")
        except:
            gym_id = "GYM1"

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            generated_otp = send_otp_to_email(gym_id, email)
            if generated_otp:
                messagebox.showinfo("✅ OTP Sent", f"OTP sent to {email}")
            else:
                messagebox.showerror("❌ Error", "Failed to send OTP.")
        else:
            messagebox.showerror("❌ Error", "Email not registered!")

    ttk.Button(frame, text="📩 Send OTP", command=send_otp).grid(row=1, column=0, columnspan=2, pady=5)

    ttk.Label(frame, text="Enter OTP:", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="e", pady=10)
    ttk.Entry(frame, textvariable=otp_var, width=30).grid(row=2, column=1, pady=10)

    ttk.Label(frame, text="New Password:", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="e", pady=10)
    ttk.Entry(frame, textvariable=new_pass_var, show="*", width=30).grid(row=3, column=1, pady=10)

    def reset_password():
        email = email_var.get().strip()
        otp_entered = otp_var.get().strip()
        new_pass = new_pass_var.get().strip()

        if otp_entered == generated_otp:
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (new_pass, email))
            conn.commit()
            messagebox.showinfo("✅ Success", "Password reset successful!")
            reset_win.destroy()
        else:
            messagebox.showerror("❌ Error", "Invalid OTP!")

    ttk.Button(frame, text="🔁 Reset Password", command=reset_password).grid(row=4, column=0, columnspan=2, pady=20)



def upload_image():
    path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
    if path:
        img = Image.open(path)
        img.thumbnail((150, 150))
        img_tk = ImageTk.PhotoImage(img)
        photo_panel.config(image=img_tk)
        photo_panel.image = img_tk
        photo_path_var.set(path)

def calculate_fees(*args):
    try:
        admission = int(admission_fees_var.get())
    except:
        admission = 0

    try:
        monthly = int(monthly_fees_var.get())
    except:
        monthly = 0

    admission_fees_var.set(str(admission))
    monthly_fees_var.set(str(monthly))

    try:
        discount = int(discount_var.get())
    except:
        discount = 0

    try:
        paid = int(paid_fees_var.get())
    except:
        paid = 0

    after_discount = monthly - discount
    after_discount_var.set(str(after_discount))

    total_due = admission + after_discount

    if paid < total_due:
        balance = total_due - paid
    else:
        balance = 0

    balance_var.set(str(balance))


try:
    with open("session.txt", "r") as f:
        session_data = f.read().strip().split(",")
        if len(session_data) == 3:
            username, role, selected_gym_id = session_data
        else:
            messagebox.showerror("Session Error", "Invalid session format.")
            exit()
except Exception as e:
    messagebox.showerror("Session Error", f"User not logged in properly.\nPlease login first.\n{e}")
    exit()



def submit_member():
    name = name_var.get()
    mobile = mobile_var.get()
    cnic = cnic_var.get()
    email = email_var.get()
    address = address_var.get()
    timing = timing_var.get()
    entry_type = entry_type_var.get()
    join_date = join_date_var.get()
    admission = admission_fees_var.get()
    monthly = monthly_fees_var.get()
    discount = discount_var.get()
    after_discount = after_discount_var.get()
    paid = paid_fees_var.get()
    balance = balance_var.get()
    photo_path = photo_path_var.get()

    # ✅ Required field check
    if not all([name, mobile, cnic, email, address, timing, entry_type, join_date, photo_path]):
        messagebox.showerror("Error", "Please fill in all required fields.")
        return

    # ✅ Get latest fingerprint member_id
    cursor.execute("SELECT MAX(member_id) FROM fingerprint_templates")
    last_member_id_row = cursor.fetchone()
    if not last_member_id_row or not last_member_id_row[0]:
        messagebox.showerror("Fingerprint Missing", "❌ Please scan your fingerprint first!")
        return

    member_id = last_member_id_row[0]

    # ❌ Prevent duplicate insert
    cursor.execute("SELECT 1 FROM members WHERE member_id = ?", (member_id,))
    if cursor.fetchone():
        messagebox.showerror("Duplicate", f"❌ This Member ID ({member_id}) is already in use.\nPlease scan new fingerprint.")
        return

    # 🧠 Type-safe number handling
    def safe_float(val):
        try:
            return float(val)
        except:
            return 0.0

    admission = safe_float(admission)
    monthly = safe_float(monthly)
    discount = safe_float(discount)
    after_discount = safe_float(after_discount)
    paid = safe_float(paid)
    balance = safe_float(balance)

    try:
        # 🧾 Insert into members
        cursor.execute('''INSERT INTO members 
            (member_id, name, mobile, cnic, address, timing, entry_type, admission_fees, email, monthly_fees, discount, after_discount, paid_fees, balance, join_date, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (member_id, name, mobile, cnic, address, timing, entry_type, admission, email, monthly, discount, after_discount, paid, balance, join_date, photo_path))
        conn.commit()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payments_data = [
            ("admission", admission),
            ("monthly fees", monthly),
            ("discount", discount),
            ("paid fees", paid),
            ("balance", balance)  # ✅ Balance also added
        ]

        for entry_type_payment, amount in payments_data:
            if amount > 0:
                # ✅ Convert amount to int if it's a whole number (like 1000.0 → 1000)
                formatted_amount = int(amount) if amount == int(amount) else amount

                cursor.execute('''INSERT INTO payments
                    (member_id, gym_id, amount, payment_method, added_by_id, added_by_name, entry_type, custom_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (member_id, selected_gym_id, formatted_amount, "cash", selected_gym_id, username, entry_type_payment, join_date))
                conn.commit()
                payment_id = cursor.lastrowid


        # 🪪 QR Card Generation
        qr = qrcode.make(mobile)
        qr_path = f"qrcodes/{mobile}.png"
        qr.save(qr_path)

        card = Image.new('RGB', (400, 250), color='white')
        qr_img = Image.open(qr_path).resize((100, 100))
        img_user = Image.open(photo_path).resize((100, 100))
        card.paste(qr_img, (10, 10))
        card.paste(img_user, (290, 10))

        draw = ImageDraw.Draw(card)
        draw.text((10, 120), f"Name: {name}", fill="black")
        draw.text((10, 150), f"Mobile: {mobile}", fill="black")
        draw.text((10, 180), f"Timing: {timing}", fill="black")

        card_path = f"cards/{mobile}_card.jpg"
        card.save(card_path)

        messagebox.showinfo("✅ Success", f"Member '{name}' (ID: {member_id}) added successfully with fingerprint.")

    except Exception as e:
        messagebox.showerror("❌ Database Error", str(e))




        # 🧾 QR Code + Card Generation
        qr = qrcode.make(mobile)
        qr_path = f"qrcodes/{mobile}.png"
        qr.save(qr_path)

        card = Image.new('RGB', (400, 250), color='white')
        qr_img = Image.open(qr_path).resize((100, 100))
        img_user = Image.open(photo_path).resize((100, 100))
        card.paste(qr_img, (10, 10))
        card.paste(img_user, (290, 10))

        draw = ImageDraw.Draw(card)
        draw.text((10, 120), f"Name: {name}", fill="black")
        draw.text((10, 150), f"Mobile: {mobile}", fill="black")
        draw.text((10, 180), f"Timing: {timing}", fill="black")

        card_path = f"cards/{mobile}_card.jpg"
        card.save(card_path)

    except sqlite3.IntegrityError as e:
        messagebox.showerror("Integrity Error", str(e))
    except Exception as e:
        messagebox.showerror("Database Error", str(e))



def show_card():
    mobile = mobile_var.get().strip()
    if not mobile:
        messagebox.showerror("Error", "Please enter mobile number first.")
        return
    card_path = os.path.abspath(f"cards/{mobile}_card.jpg")
    if os.path.exists(card_path):
        os.startfile(card_path)
    else:
        messagebox.showerror("Error", f"Card file not found: {card_path}")

def scan_qr():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    while True:
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Webcam could not be opened.")
            break

        data, bbox, _ = detector.detectAndDecode(frame)
        if bbox is not None:
            for i in range(len(bbox)):
                pt1 = tuple(map(int, bbox[i][0]))
                pt2 = tuple(map(int, bbox[(i+1) % len(bbox)][0]))
                cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)

            if data:
                mobile = data.strip()
                now = datetime.datetime.now()
                cursor.execute("SELECT name FROM members WHERE mobile = ?", (mobile,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("INSERT INTO attendance (mobile, name, date, time) VALUES (?, ?, ?, ?)",
                                   (mobile, row[0], now.date(), now.time().strftime('%H:%M:%S')))
                    conn.commit()
                    cap.release()
                    cv2.destroyAllWindows()
                    messagebox.showinfo("Attendance", f"Attendance marked for {row[0]}.")
                    return
                else:
                    cap.release()
                    cv2.destroyAllWindows()
                    messagebox.showerror("Not Found", "Member record not found.")
                    return

        cv2.imshow("QR Scanner - Press Q to Quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def search_member():
    mobile = search_var.get()
    cursor.execute("SELECT * FROM members WHERE mobile = ?", (mobile,))
    row = cursor.fetchone()
    if row:
        cursor.execute("SELECT * FROM attendance WHERE mobile = ?", (mobile,))
        attendance = cursor.fetchall()
        info = f"Name: {row[1]}\nCNIC: {row[3]}\nAddress: {row[4]}\nTiming: {row[5]}\nAdmission Fees: {row[6]}\nMonthly Fees: {row[7]}\nDiscount: {row[8]}\nAfter Discount: {row[9]}\nPaid: {row[10]}\nBalance: {row[11]}\nJoin Date: {row[13]}\n\nAttendance:\n"
        for a in attendance:
            info += f"{a[3]} {a[4]}\n"
        messagebox.showinfo("Member Info", info)
    else:
        messagebox.showerror("Error", "Member not found.")

# --- GUI Setup ---
import tkinter as tk
from tkinter import ttk

# --- GUI Setup ---
root = tk.Tk()
root.title("🏋️ Gym Management System")
root.geometry("1000x600")
root.configure(bg="#ffffff")

gym_label_var = tk.StringVar()  # only declare here

# Read session.txt
selected_gym_id = None
username = ""
role = ""
try:
    with open("session.txt", "r") as f:
        session_data = f.read().strip().split(",")
        if len(session_data) == 3:
            username, role, selected_gym_id = session_data
            gym_label_var.set(f"🏋️ Current Gym: {selected_gym_id}")  # ✅ value set here
        else:
            raise ValueError("Invalid session format")
except Exception as e:
    messagebox.showerror("Session Error", "User not logged in properly.")
    sys.exit()

# Label
gym_label = ttk.Label(root, textvariable=gym_label_var, font=("Arial", 17, "bold"), foreground="green")
gym_label.pack(pady=(5, 0))

# --- Styles ---
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Arial", 12), padding=6)
style.configure("TLabel", font=("Arial", 12))
style.configure("TEntry", font=("Arial", 12))
style.configure("Sidebar.TButton", font=("Arial", 11), padding=8, background="#e6e6e6", foreground="#000000", relief="flat")
style.map("Sidebar.TButton", background=[("active", "#d0d0d0")])

# --- Main Frames ---
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

menu_frame = tk.Frame(main_frame, width=220, bg="#f0f0f0")
menu_frame.pack(side="left", fill="y", pady=20)

content_frame = ttk.Frame(main_frame)
content_frame.pack(side="right", fill="both", expand=True)

from itertools import cycle
from PIL import Image, ImageTk

# --- Setup Slideshow ---
image_paths = [
    "images/gym.jpg",
    "images/gym1.jpg",
    "images/gym2.jpg",
    "images/gym3.jpg",
    "images/gym4.jpg"
]

# Filter only existing images
image_paths = [img for img in image_paths if os.path.exists(img)]
if not image_paths:
    print("❌ No valid images found in the 'images' folder.")
    image_paths = ["images/gym.jpg"]  # fallback

image_cycle = cycle(image_paths)
bg_label = tk.Label(content_frame)
bg_label.place(relx=0.5, rely=0.5, anchor="center")
bg_image = None  # Global reference

def update_slideshow():
    global bg_image
    try:
        current_path = next(image_cycle)
        img = Image.open(current_path).resize((780, 550), Image.Resampling.LANCZOS)
        bg_image = ImageTk.PhotoImage(img)
        bg_label.configure(image=bg_image)
        bg_label.image = bg_image
    except Exception as e:
        print(f"Error: {e}")

    root.after(3000, update_slideshow)  # every 3 seconds

update_slideshow()

# Optional: Text Over Background
tk.Label(
    content_frame,
    text="Welcome to Gym Management System",
    font=("Segoe UI", 20, "bold"),
    bg="#000000",
    fg="white"
).place(relx=0.5, rely=0.1, anchor="n")

# --- User Info Stylish Box ---
user_info_frame = tk.Frame(menu_frame, bg="#f5f5f5", bd=1, relief="groove")
user_info_frame.pack(fill="x", pady=(10, 20), padx=10)

icon_label = tk.Label(user_info_frame, text="👤", font=("Arial", 18), bg="#f5f5f5")
icon_label.pack(side="left", padx=5, pady=5)

info_text = f"{username.title()}\n{role.title()}"
text_label = tk.Label(user_info_frame, text=info_text, font=("Arial", 11, "bold"), justify="left", bg="#f5f5f5")
text_label.pack(side="left", padx=5, pady=5)

# --- Tabs ---
member_tab = ttk.Frame(content_frame)
attendance_tab = ttk.Frame(content_frame)
info_tab = ttk.Frame(content_frame)

for frame in (member_tab, attendance_tab, info_tab):
    frame.place(relwidth=1, relheight=1)

def show_frame(f):
    f.tkraise()

# --- Sidebar Buttons ---
ttk.Button(menu_frame, text="➕ Add Member", style="Sidebar.TButton", command=lambda: show_frame(member_tab)).pack(fill="x", padx=10, pady=5)

btn_register = ttk.Button(menu_frame, text="📝 Register User", style="Sidebar.TButton", command=open_register_window)
btn_register.pack(fill="x", padx=10, pady=5)

ttk.Button(menu_frame, text="📝 Member Info", style="Sidebar.TButton", command=open_member_search).pack(fill="x", padx=10, pady=5)
ttk.Button(menu_frame, text="🚪 Add Payment", style="Sidebar.TButton", command=open_payment_window).pack(fill="x", padx=10, pady=5)
ttk.Button(menu_frame, text="🚪 Add Attendance", style="Sidebar.TButton", command=open_finger).pack(fill="x", padx=10, pady=5)
ttk.Button(menu_frame, text="📊 Financial Report", style="Sidebar.TButton", command=lambda: open_financial_report(selected_gym_id)).pack(fill="x", padx=10, pady=5)

btn_settings = ttk.Button(menu_frame, text="⚙️ Settings", style="Sidebar.TButton", command=open_settings)
btn_settings.pack(fill="x", padx=10, pady=5)

ttk.Button(menu_frame, text="🚪 Log out", style="Sidebar.TButton", command=logout).pack(fill="x", padx=10, pady=5)
ttk.Button(menu_frame, text="❌ Exit", style="Sidebar.TButton", command=root.quit).pack(fill="x", padx=10, pady=5)

# --- Member Tab Frames ---
member_left = ttk.Frame(member_tab)
member_left.pack(side="left", fill="both", expand=True, padx=20, pady=20)

member_right = ttk.Frame(member_tab)
member_right.pack(side="right", fill="y", padx=20, pady=20)

# --- Start The

# --- Enhanced Member Form UI ---

# Input Variables
name_var = tk.StringVar()
mobile_var = tk.StringVar()
cnic_var = tk.StringVar()
address_var = tk.StringVar()
timing_var = tk.StringVar()
entry_type_var = tk.StringVar(value="Admission")
admission_fees_var = tk.StringVar()
email_var = tk.StringVar()
join_date_var = tk.StringVar()
monthly_fees_var = tk.StringVar()
discount_var = tk.StringVar()
after_discount_var = tk.StringVar()
paid_fees_var = tk.StringVar()
balance_var = tk.StringVar()
photo_path_var = tk.StringVar()

# Auto-calculate fees
for var in [admission_fees_var, monthly_fees_var, discount_var, paid_fees_var]:
    var.trace("w", calculate_fees)

# Form Fields
fields = [
    ("Name", name_var),
    ("Mobile", mobile_var),
    ("CNIC", cnic_var),
    ("Address", address_var),
    ("Timing", timing_var),
    ("Entry Type", entry_type_var),
    ("Join Date", join_date_var),
    ("Email", email_var),
    ("Admission Fees", admission_fees_var),
    ("Monthly Fees", monthly_fees_var),
    ("Discount", discount_var),
    ("Paid Fees", paid_fees_var),
    ("After Discount", after_discount_var),
    ("Balance", balance_var),
]

# Styled Fields Left Panel
for text, var in fields:
    frame = ttk.Frame(member_left)
    frame.pack(fill="x", pady=6, padx=5)

    label = ttk.Label(frame, text=f"{text}:", width=18, anchor="w")
    label.pack(side="left", padx=(5, 0))

    if text.lower() == "join date":
        DateEntry(
            frame,
            textvariable=var,
            width=28,
            background='darkblue',
            foreground='white',
            date_pattern='dd-mm-yyyy'
        ).pack(side="left", padx=5)
    else:
        ttk.Entry(
            frame,
            textvariable=var,
            state="normal" if text in [
                "Name", "Mobile", "CNIC", "Address", "Timing", "Email",
                "Admission Fees", "Monthly Fees", "Paid Fees", "Discount"
            ] else "readonly",
            width=30
        ).pack(side="left", padx=5)

# Right Side - Photo Upload + Buttons
photo_frame = ttk.LabelFrame(member_right, text="Upload Member Photo", padding=20)
photo_frame.pack(pady=10, padx=(0, 30), fill="both", expand=True)

photo_panel = ttk.Label(photo_frame)
photo_panel.pack(pady=10)

# Buttons with spacing and clarity
btn_upload = ttk.Button(photo_frame, text="📁 Upload Photo", style="Sidebar.TButton", command=upload_image)
btn_upload.pack(pady=5, fill="x")

btn_fingerprint = ttk.Button(photo_frame, text="🖐️ Fingerprint Scan", style="Sidebar.TButton", command=open_finger)
btn_fingerprint.pack(pady=5, fill="x")

btn_submit = ttk.Button(photo_frame, text="💾 Save Member", style="Sidebar.TButton", command=submit_member)
btn_submit.pack(pady=10, fill="x")

# Optional future button
# ttk.Button(photo_frame, text="🪪 Show Card", style="Sidebar.TButton", command=show_card).pack(pady=5)

# Attendance Tab
ttk.Button(attendance_tab, text="📸 Scan QR", style="Sidebar.TButton", command=scan_qr).pack(pady=20)

# Info Tab Search (can be styled similarly when enabled)
search_var = tk.StringVar()
# ttk.Label(info_tab, text="Enter Member Mobile Number").pack(anchor='center', pady=15, padx=15)
# search_entry = ttk.Entry(info_tab, textvariable=search_var, width=30)
# search_entry.pack(padx=10, pady=5)
# search_button = ttk.Button(info_tab, text="🔎 Search", command=search_member, width=20)
# search_button.pack(pady=10)

# Default Message
# Default Background Image (gym.jpg)
try:
    bg_img_path = "images/gym.jpg"
    if os.path.exists(bg_img_path):
        bg_image = Image.open(bg_img_path)
        bg_image = bg_image.resize((780, 550), Image.Resampling.LANCZOS)
        bg_photo = ImageTk.PhotoImage(bg_image)

        bg_label = tk.Label(content_frame, image=bg_photo)
        bg_label.image = bg_photo
        bg_label.place(relx=0.5, rely=0.5, anchor="center")
    else:
        ttk.Label(content_frame, text="Welcome to Gym Management", font=("Arial", 16), foreground="#888").place(relx=0.5, rely=0.5, anchor="center")
except Exception as e:
    print("❌ Error loading background image:", e)



if __name__ == "__main__":
    root.withdraw()
    def unlock_gui_after_gym_selected():
        root.deiconify()

    

root.deiconify()  # GUI دکھائیں

# Admin restrictions
if role.lower() != "admin":
    btn_register.state(["disabled"])
    btn_settings.state(["disabled"])

root.mainloop()