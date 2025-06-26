import smtplib
from email.message import EmailMessage
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import qrcode
import sqlite3
import io
import os
import platform
import subprocess
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4



def open_financial_report(selected_gym_id):
    
    conn = sqlite3.connect("gym.db")
    cursor = conn.cursor()

    report_win = tk.Toplevel()
    report_win.title("📊 Financial Report")
    report_win.geometry("1000x600")
    report_win.configure(bg="#ffffff")

    search_var = tk.StringVar()

    tk.Label(report_win, text="Search by ID, Entry Type or Date", font=("Segoe UI", 14, "bold"), bg="#ffffff", fg="#34495e").pack(pady=(20, 10))

    search_frame = tk.Frame(report_win, bg="#ffffff")
    search_frame.pack()

    search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Segoe UI", 11), width=35, bd=2, relief="groove")
    search_entry.pack(side="left", padx=(0, 10))

    tk.Button(search_frame, text="🔍 Search", command=lambda: load_report(), font=("Segoe UI", 11, "bold"), bg="#3498db", fg="white").pack(side="left")

    columns = ("ID", "Entry Type", "Date", "Amount")
    tree = ttk.Treeview(report_win, columns=columns, show="headings", height=18)

    style = ttk.Style()
    style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

    for col, width in zip(columns, [250, 150, 120, 150]):
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="center")

    tree.pack(fill="both", expand=True, padx=20, pady=10)

    tk.Button(report_win, text="🗑️ Delete Selected", command=lambda: delete_selected(tree, cursor, conn), font=("Segoe UI", 11), bg="#e74c3c", fg="white").pack(pady=5)

    def load_report():
        keyword = search_var.get()
        tree.delete(*tree.get_children())

        query = '''
        SELECT
            
            p.payment_id, 
            p.member_id, 
            p.added_by_id, 
            p.entry_type, 
            p.custom_date, 
            p.amount, 
            p.added_by_name
        FROM payments p
        JOIN members m ON p.member_id = m.member_id
        WHERE 
            CAST(p.payment_id AS TEXT) LIKE ? OR 
            CAST(p.member_id AS TEXT) LIKE ? OR 
            CAST(p.added_by_id AS TEXT) LIKE ? OR 
            p.entry_type LIKE ? OR 
            p.custom_date LIKE ? OR
            m.name LIKE ? OR 
            m.mobile LIKE ?
        '''
        cursor.execute(query, ('%' + keyword + '%',) * 7)
        rows = cursor.fetchall()

        for row in rows:
            payment_id, member_id, added_by_id, entry_type, date, amount, added_by_name = row
            combined_id = f"{selected_gym_id}-{member_id}-{payment_id}"

            try:
                amount_val = float(amount)
            except Exception:
                amount_val = 0.0

            date_str = date[:10] if date else ''

            tree.insert("", "end", values=(
                combined_id, entry_type, date_str, f"{amount_val:.2f}"
            ))

    def show_slip(event=None):
        selected_items = tree.selection()
        if not selected_items:
            return
        selected = selected_items[0]
        values = tree.item(selected, "values")
        if not values:
            return

        combined_id, entry_type, date, amount_str = values
        try:
            added_by_id, member_id, payment_id = combined_id.split("-")
        except ValueError:
            messagebox.showerror("Error", "Selected item ID format is invalid.")
            return

        cursor.execute('''
            SELECT amount, member_id, payment_method, added_by_name, entry_type, custom_date
            FROM payments
            WHERE payment_id=? AND member_id=? AND added_by_id=? LIMIT 1
        ''', (payment_id, member_id, added_by_id))
        payment_data = cursor.fetchone()
        if not payment_data:
            messagebox.showerror("Error", "Payment data not found.")
            return

        amount, member_id_db, payment_method, added_by_name, entry_type_db, custom_date = payment_data

        if entry_type_db.strip().lower() not in ["paid fees", "monthly"]:
            messagebox.showwarning("Not Allowed", "Only 'Paid Fees' slips can be generated.")
            return

        amount_val = float(amount or 0)

        cursor.execute('''
            SELECT name, mobile, email, balance
            FROM members
            WHERE member_id=? LIMIT 1
        ''', (member_id,))
        member_data = cursor.fetchone()
        if not member_data:
            messagebox.showerror("Error", "Member data not found.")
            return

        member_name, mobile, email, balance = member_data
        current_balance = float(balance or 0.0)

        qr_data = combined_id
        qr_img = qrcode.make(qr_data)
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        qr_pil = Image.open(buffer)
        qr_tk = ImageTk.PhotoImage(qr_pil.resize((120, 120)))

        slip = tk.Toplevel(report_win)
        slip.title("🧾 Payment Slip")
        slip.geometry("460x630")
        slip.configure(bg="#f1f1f1")

        content_frame = tk.Frame(slip, bg="white", bd=2, relief="ridge")
        content_frame.pack(padx=15, pady=15, fill="both", expand=True)

        tk.Label(content_frame, text="🧾 Payment Receipt", font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(pady=(10, 5))

        def add_row(label, value, bold=False):
            font = ("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10)
            fg = "#16a085" if bold else "#2c3e50"
            row = tk.Frame(content_frame, bg="white")
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=f"{label}:", font=font, bg="white", anchor="w", width=15).pack(side="left")
            tk.Label(row, text=value, font=font, bg="white", fg=fg, anchor="w").pack(side="left")

        add_row("Combined ID", combined_id)
        add_row("Name", member_name)
        add_row("Mobile", mobile)
        add_row("Email", email)
        add_row("Date", custom_date)
        add_row("Amount", f"Rs {amount_val:.2f}", bold=True)
        add_row("Due Amount", f"Rs {current_balance:.2f}", bold=True)
        add_row("Entry Type", entry_type_db)
        add_row("Method", payment_method)
        add_row("Added By", added_by_name)

        tk.Label(content_frame, image=qr_tk, bg="white").pack(pady=10)
        slip.qr_tk = qr_tk

        btn_frame = tk.Frame(slip, bg="#f1f1f1")
        btn_frame.pack(pady=5)

        def print_slip():
            filename = f"Slip_{payment_id}.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, height - 100, "🧾 Gym Payment Receipt")

            c.setFont("Helvetica", 12)
            c.drawString(100, height - 150, f"Combined ID: {combined_id}")
            c.drawString(100, height - 170, f"Name: {member_name}")
            c.drawString(100, height - 190, f"Mobile: {mobile}")
            c.drawString(100, height - 210, f"Email: {email}")
            c.drawString(100, height - 230, f"Date: {custom_date}")
            c.drawString(100, height - 250, f"Amount: Rs {amount_val:.2f}")
            c.drawString(100, height - 270, f"Entry Type: {entry_type_db}")
            c.drawString(100, height - 290, f"Payment Method: {payment_method}")
            c.drawString(100, height - 310, f"Added By: {added_by_name}")

            qr_path = f"qr_{payment_id}.png"
            qr_img.save(qr_path)
            c.drawImage(qr_path, width - 220, height - 220, width=100, height=100)

            c.save()
            if os.path.exists(qr_path):
                os.remove(qr_path)

            try:
                if platform.system() == "Windows":
                    os.startfile(filename)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", filename])
                else:
                    subprocess.call(["xdg-open", filename])
            except Exception as e:
                messagebox.showwarning("Open File", f"Could not open PDF automatically.\n{e}")

            messagebox.showinfo("PDF Generated", f"Slip saved as {filename}")

        def send_email():
            try:
                if not selected_gym_id:
                    messagebox.showerror("No Gym Selected", "Please select a Gym ID first.")
                    return

                conn = sqlite3.connect("gym.db")
                cursor = conn.cursor()
                cursor.execute("SELECT sender_email, sender_password FROM email_config WHERE gym_id = ?", (selected_gym_id,))
                row = cursor.fetchone()
                conn.close()

                if not row:
                    messagebox.showerror("No Email Found", f"No email configuration found for Gym ID: {selected_gym_id}")
                    return

                sender_email, sender_password = row

                qr_path = f"qr_{payment_id}.png"
                qr_img.save(qr_path)

                msg = EmailMessage()
                msg['Subject'] = 'Your Gym Payment Slip'
                msg['From'] = sender_email
                msg['To'] = email
                msg.set_content(
                    f"Dear {member_name},\n\n"
                    f"Please find your payment slip below:\n\n"
                    f"Combined ID: {combined_id}\n"
                    f"Amount: Rs {amount_val:.2f}\n"
                    f"Date: {custom_date}\n\n"
                    f"Thank you."
                )

                with open(qr_path, 'rb') as f:
                    file_data = f.read()
                    file_name = os.path.basename(qr_path)
                    msg.add_attachment(file_data, maintype='image', subtype='png', filename=file_name)

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(sender_email, sender_password)
                    smtp.send_message(msg)

                os.remove(qr_path)
                messagebox.showinfo("Email Sent", f"Slip sent to {email}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to send email.\n{e}")

        tk.Button(btn_frame, text="🖨️ Print Slip", command=print_slip, font=("Segoe UI", 10), bg="#2980b9", fg="white", width=14).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📧 Send Email", command=send_email, font=("Segoe UI", 10), bg="#27ae60", fg="white", width=14).pack(side="left", padx=5)
    
    def delete_selected():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a row to delete.")
            return

        selected = selected_items[0]
        values = tree.item(selected, "values")
        if not values:
            return

        combined_id = values[0]
        try:
            added_by_id, member_id, payment_id = combined_id.split("-")
        except ValueError:
            messagebox.showerror("Error", "Selected item ID format is invalid.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete payment ID {payment_id}?")
        if not confirm:
            return

        try:
            cursor.execute("DELETE FROM payments WHERE payment_id = ?", (payment_id,))
            conn.commit()
            tree.delete(selected)
            messagebox.showinfo("Deleted", f"Payment record {payment_id} has been deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete record.\n{e}")

    tree.bind("<Double-1>", show_slip)
    tree.bind("<Return>", show_slip)

    load_report()  # load initial data
    report_win.mainloop()
