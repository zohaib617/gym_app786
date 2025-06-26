# --- Attractive Payment Window in Form Layout ---
# --- Attractive Payment Window in Form Layout ---
def open_payment_window():
    import tkinter as tk
    from tkinter import ttk, messagebox
    import sqlite3
    from datetime import datetime
    import qrcode
    from PIL import Image, ImageTk
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    conn = sqlite3.connect("gym.db")
    cursor = conn.cursor()

    try:
        with open("session.txt", "r") as f:
            logged_in_user_id,  logged_in_user_name, gym_id = f.read().strip().split(",")
    except:
        logged_in_user_id = 1
        logged_in_user_name = "Admin"

    conn.commit()

    def submit_payment():
        member_id = member_id_var.get().strip()
        amount = amount_var.get().strip()
        method = method_var.get()
        custom_date = date_var.get().strip()

        if not member_id or not amount or not custom_date:
            messagebox.showerror("Error", "All fields are required")
            return

        try:
            total_payment = int(amount)
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number")
            return

        try:
            datetime.strptime(custom_date, '%d-%m-%Y')
        except ValueError:
            messagebox.showerror("Error", "Date format should be DD-MM-YYYY")
            return

        # --- Check for existing balance entry ---
        cursor.execute("""
            SELECT payment_id, amount FROM payments 
            WHERE member_id = ? AND entry_type = 'balance' 
            ORDER BY payment_id DESC LIMIT 1
        """, (member_id,))
        balance_row = cursor.fetchone()

        # --- Check for existing Monthly entry ---
        cursor.execute("""
            SELECT payment_id, amount FROM payments 
            WHERE member_id = ? AND entry_type = 'Monthly' 
            ORDER BY payment_id DESC LIMIT 1
        """, (member_id,))
        monthly_row = cursor.fetchone()

        # --- Default value ---
        remaining_payment = total_payment

        if balance_row:
            balance_payment_id, balance_amount = balance_row
            try:
                balance_amount = int(balance_amount)
            except ValueError:
                messagebox.showerror("Error", "Invalid balance amount format.")
                return

            if total_payment < balance_amount:
                messagebox.showerror("Error", f"Payment is less than balance ({balance_amount}).")
                return

            # Clear balance to 0
            cursor.execute("UPDATE payments SET amount = 0 WHERE payment_id = ?", (balance_payment_id,))
            remaining_payment = total_payment - balance_amount

        if monthly_row:
            monthly_payment_id, monthly_amount = monthly_row
            try:
                monthly_amount = int(monthly_amount)
            except ValueError:
                messagebox.showerror("Error", "Invalid monthly amount format.")
                return

            new_monthly_total = monthly_amount + remaining_payment
            cursor.execute("UPDATE payments SET amount = ? WHERE payment_id = ?", (new_monthly_total, monthly_payment_id))
            conn.commit()
            messagebox.showinfo("Success", f"Balance cleared and {remaining_payment} added to Monthly.")

        else:
            # Create new Monthly entry
            cursor.execute("""
                INSERT INTO payments 
                (gym_id, member_id, amount, payment_method, added_by_id, added_by_name, entry_type, custom_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gym_id, member_id, remaining_payment, method,
                gym_id, logged_in_user_name, "Monthly", custom_date
            ))
            conn.commit()

            if balance_row:
                messagebox.showinfo("Success", f"Balance cleared and {remaining_payment} saved as new Monthly entry.")
            else:
                messagebox.showinfo("Success", f"No previous balance or monthly entry found. New monthly entry added: {remaining_payment}")

        # --- Clear form ---
        member_id_var.set("")
        amount_var.set("")
        method_var.set("Cash")
        entry_type_var.set("Payment")
        date_var.set(datetime.today().strftime('%d-%m-%Y'))
        search_var.set("")
        suggestion_listbox.place_forget()


    def show_payment_slip(payment_id, member_id, member_name, mobile, email, amount, method, date, updated_balance):
        slip_win = tk.Toplevel()
        slip_win.title("Payment Slip")
        slip_win.geometry("400x600")
        slip_win.configure(bg="#ffffff")

        slip_text = (
            f"--- Payment Slip ---\n\n"
            f"combine id: {gym_id}\n"
            f"Member ID: {member_id}\n"
            f"Payment ID: {payment_id}\n"
            f"Member Name: {member_name}\n"
            f"Mobile: {mobile}\n"
            f"Email: {email}\n"
            f"Paid Fees (Amount): {amount}\n"
            f"Updated Balance: {updated_balance}\n"
            f"Date: {date}\n\n"
            "Thank you for your payment!"
        )

        tk.Label(slip_win, text=slip_text, font=("Arial", 12), justify=tk.LEFT, bg="#ffffff").pack(pady=10)

        qr_data = f"payment_id:{payment_id}_member_id:{member_id}"
        qr_img = qrcode.make(qr_data).resize((150, 150))
        qr_photo = ImageTk.PhotoImage(qr_img)
        tk.Label(slip_win, image=qr_photo, bg="#ffffff").pack(pady=10)
        slip_win.qr_photo = qr_photo

        def print_to_pdf():
            filename = f"PaymentSlip_{payment_id}.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y, "Payment Slip")
            y -= 40
            for line in slip_text.split('\n'):
                c.setFont("Helvetica", 12)
                c.drawString(50, y, line)
                y -= 20
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            pil_img = Image.open(qr_buffer)
            c.drawInlineImage(pil_img, 50, y - 150, width=150, height=150)
            c.showPage()
            c.save()
            messagebox.showinfo("PDF Saved", f"Payment slip saved as {filename}")

        ttk.Button(slip_win, text="🖨️ Print to PDF", style="Sidebar.TButton", command=print_to_pdf).pack(pady=20)

    # --- Styled Payment Form ---
    payment_window = tk.Toplevel()
    payment_window.title("💳 Add Member Payment")
    payment_window.geometry("500x350")
    payment_window.configure(bg="#f5f5f5")

    form_frame = ttk.Frame(payment_window)
    form_frame.pack(padx=20, pady=20, fill="x")

    label_font = ('Arial', 12)
    entry_font = ('Arial', 12)

    # --- Search Box ---
    search_label = ttk.Label(form_frame, text="🔍 Search Member:", font=label_font)
    search_label.grid(row=0, column=0, sticky="w", pady=5)
    search_var = tk.StringVar()
    search_entry = ttk.Entry(form_frame, textvariable=search_var, font=entry_font, width=30)
    search_entry.grid(row=0, column=1, pady=5)

    suggestion_listbox = tk.Listbox(payment_window, font=('Arial', 10), height=5)

    def update_suggestions(event=None):
        typed = search_var.get().strip()
        suggestion_listbox.delete(0, tk.END)
        if typed:
            cursor.execute("SELECT member_id, name FROM members WHERE CAST(member_id AS TEXT) LIKE ? OR name LIKE ?", (f"%{typed}%", f"%{typed}%"))
            results = cursor.fetchall()
            for member_id, name in results:
                suggestion_listbox.insert(tk.END, f"{member_id} - {name}")
            x = search_entry.winfo_rootx() - payment_window.winfo_rootx()
            y = search_entry.winfo_rooty() - payment_window.winfo_rooty() + search_entry.winfo_height()
            suggestion_listbox.place(x=x, y=y, width=300)
        else:
            suggestion_listbox.place_forget()

    def fill_from_listbox(event):
        try:
            selected = suggestion_listbox.get(suggestion_listbox.curselection())
            member_id, _ = selected.split(" - ", 1)
            member_id_var.set(member_id.strip())
            suggestion_listbox.place_forget()
            search_var.set(selected)
        except Exception:
            pass

    search_entry.bind("<KeyRelease>", update_suggestions)
    suggestion_listbox.bind("<<ListboxSelect>>", fill_from_listbox)

    # --- Form Fields Grid ---
    def add_form_row(label, var, row):
        ttk.Label(form_frame, text=label + ":", font=label_font).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(form_frame, textvariable=var, font=entry_font, width=30).grid(row=row, column=1, pady=5)

    member_id_var = tk.StringVar()
    ttk.Label(form_frame, text="Member ID:", font=label_font).grid(row=1, column=0, sticky="w", pady=5)
    ttk.Entry(form_frame, textvariable=member_id_var, font=entry_font, width=30, state="readonly").grid(row=1, column=1, pady=5)

    amount_var = tk.StringVar()
    add_form_row("Amount", amount_var, 2)

    ttk.Label(form_frame, text="Payment Method:", font=label_font).grid(row=3, column=0, sticky="w", pady=5)
    method_var = tk.StringVar(value="Cash")
    ttk.Combobox(form_frame, textvariable=method_var, values=["Cash", "Card", "Bank"], font=entry_font, state="readonly").grid(row=3, column=1, pady=5)

    ttk.Label(form_frame, text="Entry Type:", font=label_font).grid(row=4, column=0, sticky="w", pady=5)
    entry_type_var = tk.StringVar(value="paid fees")
    ttk.Combobox(form_frame, textvariable=entry_type_var, values=["paid fees"], font=entry_font, state="readonly").grid(row=4, column=1, pady=5)

    ttk.Label(form_frame, text="Date (DD-MM-YYYY):", font=label_font).grid(row=5, column=0, sticky="w", pady=5)
    date_var = tk.StringVar(value=datetime.today().strftime('%d-%m-%Y'))
    ttk.Entry(form_frame, textvariable=date_var, font=entry_font, width=30).grid(row=5, column=1, pady=5)

    # --- Save Button ---
    ttk.Button(payment_window, text="💾 Save Payment", style="Sidebar.TButton", command=submit_payment).pack(pady=20)

    def on_close():
        conn.close()
        payment_window.destroy()

    payment_window.protocol("WM_DELETE_WINDOW", on_close)
