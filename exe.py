import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import os

# Ensure database and members table exist
with sqlite3.connect("gym.db") as conn:
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            gym_id TEXT,
            name TEXT,
            mobile TEXT UNIQUE,
            cnic TEXT,
            address TEXT,
            timing TEXT,
            entry_type TEXT,
            admission_fees TEXT,
            email TEXT,
            monthly_fees TEXT,
            discount TEXT,
            after_discount TEXT,
            paid_fees TEXT,
            balance INTEGER,
            join_date TEXT,
            photo_path TEXT
        )
    ''')

def open_member_search():
    def fetch_matching_names(prefix):
        with sqlite3.connect("gym.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM members WHERE name LIKE ?", (prefix + '%',))
            return [row[0] for row in cursor.fetchall()]

    def fetch_member_profile(name):
        with sqlite3.connect("gym.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE name = ?", (name,))
            return cursor.fetchone()

    def on_keyrelease(event):
        value = search_var.get()
        if value == "":
            suggestion_box.place_forget()
            return
        names = fetch_matching_names(value)
        if not names:
            suggestion_box.place_forget()
            return
        suggestion_box.delete(0, tk.END)
        for item in names:
            suggestion_box.insert(tk.END, item)
        x = search_entry.winfo_x()
        y = search_entry.winfo_y() + search_entry.winfo_height()
        suggestion_box.place(x=x + 125, y=y + 5)

    def on_select(event=None):
        try:
            selected = suggestion_box.get(suggestion_box.curselection())
            search_var.set(selected)
            suggestion_box.place_forget()
            data = fetch_member_profile(selected)
            if data:
                show_member_profile(data)
        except:
            pass

    def clear_profile():
        for key in entry_vars:
            entry_vars[key].set("")
            entry_widgets[key].config(state='normal')
        show_placeholder()

    def show_placeholder():
        try:
            default_img_path = "images/default_profile.png"
            if os.path.exists(default_img_path):
                img = Image.open(default_img_path).resize((200, 200))
                photo = ImageTk.PhotoImage(img)
                photo_label.config(image=photo, text="", bg="#ffffff")
                photo_label.image = photo
            else:
                photo_label.config(image="", text="No Image Available", bg="#e0e0e0")
                photo_label.image = None
        except Exception as e:
            print("Placeholder load error:", e)
            photo_label.config(image="", text="Error loading image", bg="#e0e0e0")
            photo_label.image = None

    def show_member_profile(data):
        (
            member_id, gym_id, name, mobile, cnic, address, timing, entry_type,
            admission_fees, email, monthly_fees, discount, after_discount,
            paid_fees, balance, join_date, photo_path
        ) = data

        # ✅ Get latest balance from payments table
        with sqlite3.connect("gym.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT amount FROM payments
                WHERE member_id = ? AND entry_type = 'balance'
                ORDER BY payment_id DESC LIMIT 1
            """, (member_id,))
            result = cursor.fetchone()
            balance = result[0] if result else 0

        values = {
            "Member ID": member_id, "Gym ID": gym_id, "Name": name, "Mobile": mobile,
            "CNIC": cnic, "Address": address, "Timing": timing,
            "Entry Type": entry_type, "Admission Fees": admission_fees,
            "Email": email, "Monthly Fees": monthly_fees, "Discount": discount,
            "After Discount": after_discount, "Paid Fees": paid_fees,
            "Balance": balance, "Join Date": join_date, "Photo Path": photo_path
        }

        for key, value in values.items():
            entry_vars[key].set(value)
            entry_widgets[key].config(state='readonly')

        try:
            if photo_path and os.path.exists(photo_path):
                img = Image.open(photo_path).resize((200, 200))
                photo = ImageTk.PhotoImage(img)
                photo_label.config(image=photo, text="", bg="#ffffff")
                photo_label.image = photo
            else:
                show_placeholder()
        except Exception as e:
            print("Image loading error:", e)
            show_placeholder()
    def enable_edit():
        for field in ["Name", "Mobile", "Email"]:
            entry_widgets[field].config(state='normal')

    def save_changes():
        member_id = entry_vars["Member ID"].get().strip()
        name = entry_vars["Name"].get().strip()
        mobile = entry_vars["Mobile"].get().strip()
        email = entry_vars["Email"].get().strip()

        if not member_id:
            messagebox.showwarning("Validation", "Search a member to update.")
            return
        if not name or not mobile or not email:
            messagebox.showwarning("Validation", "Name, Mobile, and Email are required.")
            return

        try:
            with sqlite3.connect("gym.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE members SET name=?, mobile=?, email=? WHERE member_id=?
                """, (name, mobile, email, member_id))
                conn.commit()
            messagebox.showinfo("Success", "Record updated successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Mobile number must be unique.")
        finally:
            for field in entry_widgets:
                entry_widgets[field].config(state='readonly')

    # === GUI ===
    root = tk.Toplevel()
    root.title("🔍 Member Search with Suggestions")
    root.geometry("880x720")
    root.configure(bg="#eef2f5")

    tk.Label(root, text="👤 Search Member", font=("Segoe UI", 20, "bold"), bg="#eef2f5").pack(pady=15)

    search_frame = tk.Frame(root, bg="#eef2f5")
    search_frame.pack()

    tk.Label(search_frame, text="Enter Name:", font=("Segoe UI", 12), bg="#eef2f5").pack(side=tk.LEFT, padx=5)
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Segoe UI", 11), width=30)
    search_entry.pack(side=tk.LEFT, padx=10)
    search_entry.bind("<KeyRelease>", on_keyrelease)

    ttk.Button(search_frame, text="Search", command=lambda: show_member_profile(fetch_member_profile(search_var.get()))).pack(side=tk.LEFT)

    suggestion_box = tk.Listbox(root, width=30, height=5, font=("Segoe UI", 10))
    suggestion_box.bind("<<ListboxSelect>>", on_select)

    profile_frame = tk.Frame(root, bg="#eef2f5")
    profile_frame.pack(pady=10)

    form_frame = tk.LabelFrame(profile_frame, text="📄 Member Info", bg="#ffffff", font=("Segoe UI", 11, "bold"), padx=10, pady=10)
    form_frame.pack(side=tk.LEFT, padx=20)

    fields = [
        "Member ID", "Gym ID", "Name", "Mobile", "CNIC", "Address", "Timing",
        "Entry Type", "Admission Fees", "Email", "Monthly Fees", "Discount",
        "After Discount", "Paid Fees", "Balance", "Join Date", "Photo Path"
    ]

    entry_vars = {}
    entry_widgets = {}

    for i, field in enumerate(fields):
        tk.Label(form_frame, text=field + ":", font=("Segoe UI", 10, "bold"), bg="#ffffff", anchor="e", width=16).grid(row=i, column=0, sticky="e", pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(form_frame, textvariable=var, width=35, font=("Segoe UI", 10))
        entry.grid(row=i, column=1, pady=3, padx=5)
        entry_vars[field] = var
        entry_widgets[field] = entry

    photo_frame = tk.LabelFrame(profile_frame, text="🖼️ Photo", bg="#ffffff", font=("Segoe UI", 11), padx=10, pady=10)
    photo_frame.pack(side=tk.LEFT, padx=20)
    photo_frame.configure(width=220, height=240)
    photo_frame.pack_propagate(False)

    photo_label = tk.Label(photo_frame, text="No Image", bg="#dcdcdc")
    photo_label.pack(fill="both", expand=True)

    btn_frame = tk.Frame(root, bg="#eef2f5")
    btn_frame.pack(pady=20)

    ttk.Button(btn_frame, text="✏️ Edit Details", command=enable_edit).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="💾 Save Changes", command=save_changes).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="🧹 Clear", command=clear_profile).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="❌ Close", command=root.destroy).pack(side=tk.LEFT, padx=10)

    show_placeholder()
    root.bind("<Return>", lambda e: show_member_profile(fetch_member_profile(search_var.get())))

# Run GUI
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_member_search()
    root.mainloop()
