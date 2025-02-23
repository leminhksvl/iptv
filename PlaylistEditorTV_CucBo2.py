import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os  # Thêm thư viện os
import subprocess  # Thêm thư viện subprocess để chạy VLC

# Thư mục chứa các file M3U (thay đổi nếu cần)
m3u_directory = "."

# URL danh sách IPTV mặc định (để trống khi làm việc với file cục bộ)
iptv_url = ""

# Biểu thức chính quy để trích xuất thông tin IPTV từ M3U
extinf_pattern = re.compile(r'#EXTINF:-?\d+(?:\s+([^,]+))?,(.+)')
attr_pattern = re.compile(r'([a-zA-Z0-9-]+)="([^"]+)"')

# Hàm xử lý file M3U
def process_m3u(content, url=""):  # Thêm url làm tham số, mặc định là ""
    lines = content.split("\n")
    channel_info = {}
    extracted_channels = []
    stt_counter = 1  # Đánh số thứ tự

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            match = extinf_pattern.search(line)
            if match:
                attributes_str = match.group(1) if match.group(1) else ""
                channel_name = match.group(2).strip()

                attributes = dict(attr_pattern.findall(attributes_str)) if attributes_str else {}

                channel_info = {
                    "STT": stt_counter,
                    "tvg-id": attributes.get("tvg-id", ""),
                    "name": channel_name,
                    "tvg-Name": attributes.get("tvg-name", ""),
                    "tvg-logo": attributes.get("tvg-logo", ""),
                    "group-title": attributes.get("group-title", ""),
                    "url": "",
                }
        elif line and not line.startswith("#"):
            channel_info["url"] = line.strip()
            extracted_channels.append(channel_info.copy())
            stt_counter += 1  # Tăng STT sau mỗi URL

    return extracted_channels

# Hàm tải danh sách IPTV từ file cục bộ
def load_local_m3u(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            channels = process_m3u(content)
            return channels
    except FileNotFoundError:
        messagebox.showerror("Lỗi", "Không tìm thấy file M3U.")
        return []
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi đọc file: {e}")
        return []

# Cập nhật danh sách IPTV từ TreeView
def update_list():
    global channels
    channels = []
    for row in tree.get_children():
        values = tree.item(row)["values"]
        channels.append({
            "STT": values[0],
            "tvg-id": values[1],
            "name": values[2],
            "tvg-Name": values[3],
            "tvg-logo": values[4],
            "group-title": values[5],
            "url": values[6],
        })

# Xóa dòng đang chọn
def delete_selected():
    selected = tree.selection()
    if selected:
        for item in selected:
            tree.delete(item)
        messagebox.showinfo("Thông báo", "Đã xóa dòng được chọn")

# Lưu danh sách IPTV vào file .m3u
def save_m3u():
    update_list()
    filepath = filedialog.asksaveasfilename(defaultextension=".m3u", filetypes=[("M3U Files", "*.m3u")])
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                extinf = f'#EXTINF:-1'
                if channel["tvg-id"]:
                    extinf += f' tvg-id="{channel["tvg-id"]}"'
                if channel["tvg-logo"]:
                    extinf += f' tvg-logo="{channel["tvg-logo"]}"'
                if channel["group-title"]:
                    extinf += f' group-title="{channel["group-title"]}"'
                if channel["tvg-Name"]:
                    extinf += f' tvg-name="{channel["tvg-Name"]}"'

                extinf += f',{channel["name"]}\n'

                f.write(extinf)
                f.write(f"{channel['url']}\n")

        print(f"Đã lưu file tại {filepath}")
        messagebox.showinfo("Thông báo", f"Đã lưu file tại: {filepath}")

# Hiển thị danh sách IPTV lên TreeView
def display_channels(filtered_list=None):
    tree.delete(*tree.get_children())  # Xóa danh sách cũ
    data = filtered_list if filtered_list is not None else channels
    for channel in data:
        try:
            tree.insert("", tk.END, values=(channel.get("STT", ""), channel.get("tvg-id", ""), channel.get("name", ""), channel.get("tvg-Name", ""), channel.get("tvg-logo", ""), channel.get("group-title", ""), channel.get("url", "")))
        except Exception as e:
            print(f"Lỗi khi chèn dữ liệu vào TreeView: {e}")
            print(f"Dữ liệu kênh gây lỗi: {channel}")

# Tìm kiếm theo từng cột
def search_channels(*args):
    filtered = [
        ch for ch in channels
        if all(str(search_entries[i].get()).lower() in str(ch[col]).lower() for i, col in enumerate(columns))
    ]
    display_channels(filtered)

# Khi chọn dòng, đưa dữ liệu lên Entry để chỉnh sửa
def on_select(event):
    selected = tree.selection()
    if selected:
        values = tree.item(selected[0])["values"]
        for i, entry in enumerate(edit_entries):
            entry.delete(0, tk.END)
            entry.insert(0, values[i])

# Cập nhật dòng được chọn sau khi chỉnh sửa
def update_selected():
    selected = tree.selection()
    values = [entry.get() for entry in edit_entries]
    if selected:
        tree.item(selected[0], values=values)
    else:
        tree.insert("", tk.END, values=values)
    messagebox.showinfo("Thông báo", "Đã update")

# Hàm phát kênh bằng VLC
def play_channel():
    selected = tree.selection()
    if selected:
        values = tree.item(selected[0])["values"]
        url = values[6]  # URL nằm ở cột thứ 7
        # Đường dẫn đến VLC (thay đổi nếu cần)
        vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
        try:
            subprocess.Popen([vlc_path,"--one-instance", url])
        except FileNotFoundError:
            messagebox.showerror("Lỗi", "Không tìm thấy VLC. Hãy chắc chắn rằng VLC đã được cài đặt và đường dẫn chính xác.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi chạy VLC: {e}")
    else:
        messagebox.showinfo("Thông báo", "Vui lòng chọn một kênh trước.")

# Hàm tải danh sách IPTV từ file cục bộ được chọn từ Combobox
def load_selected_m3u():
    selected_file = m3u_combo.get()
    if selected_file:
        filepath = os.path.join(m3u_directory, selected_file)
        global channels
        channels = load_local_m3u(filepath)
        display_channels(channels)
        messagebox.showinfo("Thông báo", f"Đã tải danh sách từ: {selected_file}")

# Hàm tải lại danh sách IPTV từ file đã chọn (nếu có)
def reload_data():
    selected_file = m3u_combo.get()
    if selected_file:
        filepath = os.path.join(m3u_directory, selected_file)
        global channels
        channels = load_local_m3u(filepath)
        display_channels()
        messagebox.showinfo("Thông báo", "Đã tải lại danh sách")
    else:
        messagebox.showinfo("Thông báo", "Chưa có file nào được tải.")

# Lấy danh sách các file M3U trong thư mục
m3u_files = [f for f in os.listdir(m3u_directory) if f.endswith(".m3u")]

# Danh sách kênh ban đầu (trống cho đến khi tải file)
channels = []

# Giao diện Tkinter
root = tk.Tk()
root.title("Quản lý IPTV List")

# Tạo Menu Bar
menubar = tk.Menu(root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Lưu file M3U", command=save_m3u)
filemenu.add_separator()
filemenu.add_command(label="Thoát", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)
root.config(menu=menubar)

# Tạo Frame chứa Combobox chọn file M3U và nút tải
combo_frame = tk.Frame(root)
combo_frame.pack(fill="x", padx=10, pady=5)

tk.Label(combo_frame, text="Chọn file M3U:").pack(side="left", padx=5)
m3u_combo = ttk.Combobox(combo_frame, values=m3u_files, state="readonly")
m3u_combo.pack(side="left", padx=5, fill="x", expand=True)

btn_load_combo = tk.Button(combo_frame, text="Tải danh sách", command=load_selected_m3u)
btn_load_combo.pack(side="left", padx=5)

# Tạo Frame chứa TreeView và thanh cuộn
frame_tree = tk.Frame(root)
frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

# Tạo thanh cuộn
scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

# Cấu trúc bảng dữ liệu
columns = ("STT", "tvg-id", "name", "tvg-Name", "tvg-logo", "group-title", "url")
tree = ttk.Treeview(frame_tree, columns=columns, show="headings", yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

# Gán thanh cuộn vào TreeView
scroll_y.config(command=tree.yview)
scroll_x.config(command=tree.xview)
scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")

# Định dạng cột
column_widths = [50, 100, 150, 100, 100, 100, 200]  # Độ rộng từng cột
for i, col in enumerate(columns):
    tree.heading(col, text=col)
    tree.column(col, width=column_widths[i])

# Đặt TreeView vào giao diện
tree.pack(expand=True, fill="both")

# Lắng nghe sự kiện chọn dòng
tree.bind("<<TreeviewSelect>>", on_select)

# Tạo Frame chứa ô tìm kiếm
search_frame = tk.Frame(root)
search_frame.pack(fill="x", padx=10, pady=5)

# Tạo các Entry tìm kiếm tương ứng với từng cột
search_entries = []
for i, col in enumerate(columns):
    entry = tk.Entry(search_frame, width=column_widths[i] // 8)  # Điều chỉnh kích thước ô tìm kiếm
    entry.pack(side="left", padx=2, fill="x", expand=True)
    entry.bind("<KeyRelease>", search_channels)
    search_entries.append(entry)

# Tạo khung nhập liệu để chỉnh sửa
edit_frame = tk.Frame(root)
edit_frame.pack(fill="x", padx=10, pady=5)

edit_entries = []
for i, col in enumerate(columns):
    tk.Label(edit_frame, text=col).pack(side="left", padx=5)
    entry = tk.Entry(edit_frame, width=column_widths[i] // 8)
    entry.pack(side="left")
    edit_entries.append(entry)

# Frame chứa các nút
frame_buttons = tk.Frame(root)
frame_buttons.pack(fill="x", padx=10, pady=5)

# Frame trung gian để căn giữa nút
frame_inner = tk.Frame(frame_buttons)
frame_inner.pack(expand=True)  # Căn giữa trong frame_buttons

# Nút Cập nhật dòng
btn_update = tk.Button(frame_inner, text="Cập nhật dòng", command=update_selected)
btn_update.pack(side="left", padx=5, pady=5)

# Nút Xóa dòng
btn_delete = tk.Button(frame_inner, text="Xóa dòng", command=delete_selected, fg="red")
btn_delete.pack(side="left", padx=5, pady=5)

# Nút Lưu file M3U
btn_save = tk.Button(frame_inner, text="Lưu danh sách M3U", command=save_m3u)
btn_save.pack(side="left", padx=5, pady=5)

# Nút Tải lại danh sách
btn_reload = tk.Button(frame_inner, text="Tải lại danh sách", command=reload_data, fg="blue")
btn_reload.pack(side="left", padx=5, pady=5)

# Nút Phát kênh
btn_play = tk.Button(frame_inner, text="Phát kênh", command=play_channel)
btn_play.pack(side="left", padx=5, pady=5)

root.mainloop()
