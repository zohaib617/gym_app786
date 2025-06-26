import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import subprocess
import os
import smtplib
import random
from email.message import EmailMessage

# --- DB Setup ---
conn = sqlite3.connect("gym.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    email TEXT UNIQUE,
    role TEXT
)''')

cursor.execute('''
INSERT OR IGNORE INTO users (username, password, email, role)
VALUES ('zohan', '7575', 'zohan@gmail.com', 'admin')
''')

conn.commit()


# ✅ Send OTP Function
def send_otp_to_email(gym_id, receiver_email):
    otp = str(random.randint(100000, 999999))

    conn2 = sqlite3.connect("gym.db")
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT sender_email, sender_password FROM email_config WHERE gym_id = ?", (gym_id,))
    row = cursor2.fetchone()
    conn2.close()

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


# ✅ Login Function
def login():
    username = username_var.get().strip()
    password = password_var.get().strip()
    gym_id = gym_id_var.get().strip()

    if not username or not password or not gym_id:
        messagebox.showerror("Login Failed", "All fields are required including Gym ID.")
        return

    cursor.execute("SELECT id, role FROM users WHERE username = ? AND password = ?", (username, password))
    row = cursor.fetchone()

    if row:
        user_id, role = row
        with open("session.txt", "w") as f:
            f.write(f"{username},{role},{gym_id}")

        messagebox.showinfo("Login Successful", f"Welcome {username} Role: {role} GYM Branch : {gym_id}")
        root.destroy()
        subprocess.Popen(["main.exe"])
    else:
        messagebox.showerror("Login Failed", "Invalid Username or Password.")


# ✅ Toggle Password Visibility
def toggle_password():
    password_entry.config(show="" if show_pass.get() else "*")


# ✅ Reset Password Window (OTP)
def open_reset_password_window():
    reset_win = tk.Toplevel(root)
    reset_win.title("🔐 Reset Password with OTP")
    reset_win.geometry("500x450")
    reset_win.resizable(False, False)

    if os.path.exists("images/gym.jpg"):
        bg_image = Image.open("images/gym.jpg").resize((500, 450), Image.Resampling.LANCZOS)
        bg_photo = ImageTk.PhotoImage(bg_image)
        tk.Label(reset_win, image=bg_photo).place(x=0, y=0, relwidth=1, relheight=1)
        reset_win.bg_photo = bg_photo
    else:
        reset_win.configure(bg="#1c1c1c")

    email_var = tk.StringVar()
    otp_var = tk.StringVar()
    new_pass_var = tk.StringVar()
    generated_otp = None

    outer_frame = tk.Frame(reset_win, bg="#2c3e50", bd=8, relief="ridge")
    outer_frame.place(relx=0.5, rely=0.5, anchor="center")

    frame = ttk.Frame(outer_frame, style="Login.TFrame", padding=30)
    frame.pack()

    ttk.Label(frame, text="🔁 Reset Your Password", style="Login.TLabel", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    ttk.Label(frame, text="Registered Email:", style="Login.TLabel").grid(row=1, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(frame, textvariable=email_var, width=30).grid(row=1, column=1, pady=5)

    def send_otp():
        nonlocal generated_otp
        email = email_var.get().strip()
        if not email:
            messagebox.showerror("❌ Error", "Please enter your registered email.")
            return

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

    ttk.Button(frame, text="📩 Send OTP", style="Login.TButton", command=send_otp).grid(row=2, column=0, columnspan=2, pady=(10, 15), ipadx=20)

    ttk.Label(frame, text="Enter OTP:", style="Login.TLabel").grid(row=3, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(frame, textvariable=otp_var, width=30).grid(row=3, column=1, pady=5)

    ttk.Label(frame, text="New Password:", style="Login.TLabel").grid(row=4, column=0, sticky="e", padx=10, pady=5)
    ttk.Entry(frame, textvariable=new_pass_var, show="*", width=30).grid(row=4, column=1, pady=5)

    def reset_password():
        email = email_var.get().strip()
        otp_entered = otp_var.get().strip()
        new_pass = new_pass_var.get().strip()

        if not email or not otp_entered or not new_pass:
            messagebox.showerror("❌ Error", "All fields are required.")
            return

        if otp_entered == generated_otp:
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (new_pass, email))
            conn.commit()
            messagebox.showinfo("✅ Success", "Password reset successful!")
            reset_win.destroy()
        else:
            messagebox.showerror("❌ Error", "Invalid OTP!")

    ttk.Button(frame, text="🔐 Reset Password", style="Login.TButton", command=reset_password).grid(row=5, column=0, columnspan=2, pady=20, ipadx=20)


# ✅ GUI Setup
root = tk.Tk()
root.title("🏋️ Gym Login System")
root.geometry("600x550")
root.resizable(False, False)

# ✅ Background Image
if os.path.exists("images/gym.jpg"):
    bg_image = Image.open("images/gym.jpg").resize((600, 550), Image.Resampling.LANCZOS)
    bg_photo = ImageTk.PhotoImage(bg_image)
    tk.Label(root, image=bg_photo).place(x=0, y=0, relwidth=1, relheight=1)
else:
    root.configure(bg="#1c1c1c")

# ✅ Style
style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Segoe UI", 11), background="#ffffff")
style.configure("TButton", font=("Segoe UI", 11), padding=6)
style.configure("TEntry", font=("Segoe UI", 11))
style.configure("Login.TFrame", background="#d0d0d0", relief="raised", borderwidth=2)
style.configure("Login.TLabel", font=("Segoe UI", 12), background="#d0d0d0")
style.configure("Login.TButton", font=("Segoe UI", 12, "bold"), background="#e6e6e6", foreground="black")
style.map("Login.TButton", background=[("active", "#d0d0d0")])

# ✅ Outer Frame
outer_frame = tk.Frame(root, bg="#2c3e50", bd=8, relief="ridge")
outer_frame.place(relx=0.5, rely=0.5, anchor="center")

form_frame = ttk.Frame(outer_frame, style="Login.TFrame", padding=30)
form_frame.pack()

ttk.Label(form_frame, text="👤 Gym Login", style="Login.TLabel", font=("Segoe UI", 18, "bold")).pack(pady=(0, 20))

# ✅ Variables
username_var = tk.StringVar()
password_var = tk.StringVar()
gym_id_var = tk.StringVar()
show_pass = tk.BooleanVar()

# ✅ Username
ttk.Label(form_frame, text="Username:", style="Login.TLabel").pack(anchor="w", pady=(5, 0))
ttk.Entry(form_frame, textvariable=username_var, width=30).pack(pady=(0, 10))

# ✅ Password
ttk.Label(form_frame, text="Password:", style="Login.TLabel").pack(anchor="w", pady=(5, 0))
password_entry = ttk.Entry(form_frame, textvariable=password_var, show="*", width=30)
password_entry.pack(pady=(0, 10))

# ✅ Gym ID
ttk.Label(form_frame, text="Select Gym ID:", style="Login.TLabel").pack(anchor="w", pady=(5, 0))
gym_id_combo = ttk.Combobox(form_frame, textvariable=gym_id_var, values=["GYM1", "GYM2", "GYM3", "GYM4"], state="readonly", width=28)
gym_id_combo.pack(pady=(0, 15))
gym_id_combo.current(0)

# ✅ Show Password
ttk.Checkbutton(form_frame, text="Show Password", variable=show_pass, command=toggle_password).pack(anchor="w", pady=(0, 15))

# ✅ Login Button
ttk.Button(form_frame, text="🔐 Login", style="Login.TButton", command=login).pack(pady=10, fill="x")

# ✅ Forgot Password
ttk.Button(form_frame, text="🔁 Forgot Password?", style="Login.TButton", command=open_reset_password_window).pack(pady=(10, 5), fill="x")

# ✅ Mainloop
root.mainloop()
