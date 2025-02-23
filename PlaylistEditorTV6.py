# Nâng cấp entry bằng list lấy dừ linkurl.txt
# Kiểm tra chất lượng url
# Thêm tính năng chạy thử url bằng vlc (vlc chạy chung)
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os
import subprocess
import threading
import vlc
import time

# URL danh sách IPTV mặc định
iptv_url = ""
# File chứa danh sách URL
LINK_URL_FILE = "linkurl.txt"

# ** Quan trọng: Thay đổi đường dẫn này cho phù hợp với vị trí VLC của bạn**
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"  # Ví dụ đường dẫn trên Windows
# VLC_PATH = "/Applications/VLC.app/Contents/MacOS/VLC"  # Ví dụ đường dẫn trên macOS
# VLC_PATH = "/usr/bin/vlc"  # Ví dụ đường dẫn trên Linux (có thể cần 'which vlc' để tìm)

# Màu sắc
WORKING_COLOR = "light green"
BROKEN_COLOR = "light coral"

# Đọc danh sách URL từ file
def load_url_list(filepath):
    try:
        with open(filepath, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
        return urls
    except FileNotFoundError:
        messagebox.showerror("Lỗi", f"Không tìm thấy file: {filepath}")
        return []
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi đọc file: {e}")
        return []

# Biểu thức chính quy để trích xuất thông tin IPTV từ M3U
extinf_pattern = re.compile(r'#EXTINF:-?\d+(?:\s+([^,]+))?,(.+)')
attr_pattern = re.compile(r'([a-zA-Z0-9-]+)="([^"]+)"')

# Hàm xử lý file M3U
def process_m3u(content, url=""):
    lines = content.split("\n")
    channel_info = {}
    extracted_channels = []
    stt_counter = 1

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
            stt_counter += 1

    return extracted_channels

# Hàm kiểm tra xem URL kênh có hoạt động không
def is_channel_working(url, timeout=2):  # Giảm timeout để kiểm tra nhanh hơn
    try:
        response = requests.head(url, timeout=timeout)
        return 399 >= response.status_code >= 200 # Thay đổi 100 thành 200 vì 1xx là informational
    except requests.RequestException:
        return False

# Hàm tải danh sách IPTV từ URL
def load_iptv_list(url):
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        content = response.text
        channels = process_m3u(content, url)
        return channels
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Lỗi", f"Lỗi khi tải URL: {e}")
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
    filepath = filedialog.asksaveasfilename(defaultextension=".m3u",
                                            filetypes=[("M3U Files", "*.m3u")])
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
    tree.delete(*tree.get_children())
    data = filtered_list if filtered_list is not None else channels
    for channel in data:
        item_id = tree.insert("", tk.END, values=(channel["STT"], channel["tvg-id"],
                                         channel["name"], channel["tvg-Name"],
                                         channel["tvg-logo"],
                                         channel["group-title"], channel["url"]))
        # Màu mặc định, sau đó sẽ được cập nhật trong thread kiểm tra
        tree.tag_configure("default", background="white")
        tree.item(item_id, tags=("default",)) # Thêm tag "default"

# Tìm kiếm theo từng cột
def search_channels(*args):
    filtered = [
        ch for ch in channels
        if all(str(search_entries[i].get()).lower() in str(ch[col]).lower()
               for i, col in enumerate(columns))
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

# Hàm tải danh sách IPTV từ URL được chọn
def load_selected_iptv():
    global iptv_url
    selected_url = url_combo.get()  # Lấy URL từ Combobox
    if selected_url:
        iptv_url = selected_url
        channels = load_iptv_list(iptv_url)
        display_channels(channels)
        # Sau khi tải xong, kiểm tra trạng thái từng kênh (có thể tốn thời gian)
        for item in tree.get_children():
            url = tree.item(item)["values"][6]
            thread = threading.Thread(target=check_url_status_and_color, args=(item, url))
            thread.start()
        messagebox.showinfo("Thông báo", "Đã tải danh sách mới")

# Hàm tải lại danh sách IPTV từ URL hiện tại
def reload_data():
    global channels
    channels = load_iptv_list(iptv_url)
    display_channels()
    # Sau khi tải xong, kiểm tra trạng thái từng kênh (có thể tốn thời gian)
    for item in tree.get_children():
        url = tree.item(item)["values"][6]
        thread = threading.Thread(target=check_url_status_and_color, args=(item, url))
        thread.start()
    messagebox.showinfo("Thông báo", "Đã tải lại danh sách")

# Hàm chạy VLC với URL của kênh được chọn
def play_selected_channel():
    selected = tree.selection()
    if selected:
        values = tree.item(selected[0])["values"]
        url = values[6]  # URL nằm ở cột thứ 7 (index 6)
        try:
            # Kiểm tra xem VLC_PATH có tồn tại không
            if not os.path.exists(VLC_PATH):
                messagebox.showerror("Lỗi", f"Không tìm thấy VLC tại đường dẫn: {VLC_PATH}.  Hãy kiểm tra lại đường dẫn.")
                return

            # Mở VLC với URL, sử dụng đường dẫn tuyệt đối
            subprocess.Popen([VLC_PATH,"--one-instance", url])
        except FileNotFoundError:
            messagebox.showerror("Lỗi", "Không tìm thấy VLC. Hãy đảm bảo VLC đã được cài đặt và đường dẫn chính xác.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi chạy VLC: {e}")
    else:
        messagebox.showinfo("Thông báo", "Vui lòng chọn một kênh trước khi phát.")

# Hàm kiểm tra chất lượng URL của kênh
def check_channel_quality():
    selected = tree.selection()
    if selected:
        values = tree.item(selected[0])["values"]
        url = values[6]  # URL nằm ở cột thứ 7 (index 6)

        # Tạo một thread để kiểm tra URL (tránh làm treo UI)
        thread = threading.Thread(target=check_url_status, args=(url,))
        thread.start()
    else:
        messagebox.showinfo("Thông báo", "Vui lòng chọn một kênh trước khi kiểm tra.")

# Hàm kiểm tra trạng thái URL (chạy trong một thread riêng)
def check_url_status(url):
    working = is_channel_working(url)
    if working:
        messagebox.showinfo("Thông báo", f"Kênh {url} có vẻ đang hoạt động.")
    else:
        messagebox.showinfo("Thông báo", f"Kênh {url} có vẻ không hoạt động.")

#Hàm kiểm tra trạng thái URL và thay đổi màu (chạy trong một thread riêng)
def check_url_status_and_color(item_id, url):
    working = is_channel_working(url)
    if working:
        tree.item(item_id, tags=("working",))
    else:
        tree.item(item_id, tags=("broken",))
    tree.update()

# Hàm xử lý sự kiện khi URL trong Combobox thay đổi
def on_url_change(event):
    global iptv_url
    selected_url = url_combo.get()
    if selected_url != iptv_url:
        iptv_url = selected_url
        channels = load_iptv_list(iptv_url)
        display_channels(channels)
        # Sau khi tải xong, kiểm tra trạng thái từng kênh (có thể tốn thời gian)
        for item in tree.get_children():
            url = tree.item(item)["values"][6]
            thread = threading.Thread(target=check_url_status_and_color, args=(item, url))
            thread.start()
        messagebox.showinfo("Thông báo", "Đã tải danh sách mới")

# Giao diện Tkinter
root = tk.Tk()
root.title("Quản lý IPTV List")

# Đọc danh sách URL từ file
url_list = load_url_list(LINK_URL_FILE)

# Tạo Frame chứa Combobox URL
url_frame = tk.Frame(root)
url_frame.pack(fill="x", padx=10, pady=5)

tk.Label(url_frame, text="IPTV URL:").pack(side="left", padx=5)
url_combo = ttk.Combobox(url_frame, values=url_list, width=50)
url_combo.pack(side="left", padx=5, fill="x", expand=True)

# Nếu có URL trong list thì lấy URL đầu tiên
if url_list:
    iptv_url = url_list[0]
    url_combo.set(iptv_url)  # Đặt URL đầu tiên vào Combobox

# Ràng buộc sự kiện thay đổi URL trong Combobox
url_combo.bind("<<ComboboxSelected>>", on_url_change)
url_combo.bind("<Return>", on_url_change)

# Tạo Frame chứa ô tìm kiếm
search_frame = tk.Frame(root)
search_frame.pack(fill="x", padx=10, pady=5)

# Tạo Frame chứa TreeView và thanh cuộn
frame_tree = tk.Frame(root)
frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

# Tạo thanh cuộn
scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

# Cấu trúc bảng dữ liệu
columns = ("STT", "tvg-id", "name", "tvg-Name", "tvg-logo", "group-title",
           "url")
tree = ttk.Treeview(frame_tree, columns=columns, show="headings",
                    yscrollcommand=scroll_y.set,
                    xscrollcommand=scroll_x.set)

# Gán thanh cuộn vào TreeView
scroll_y.config(command=tree.yview)
scroll_x.config(command=tree.xview)
scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")

# Định dạng cột
column_widths = [50, 100, 150, 100, 100, 100, 200]
for i, col in enumerate(columns):
    tree.heading(col, text=col)
    tree.column(col, width=column_widths[i])

# Cấu hình màu sắc cho tag
tree.tag_configure("working", background=WORKING_COLOR)
tree.tag_configure("broken", background=BROKEN_COLOR)

# Đặt TreeView vào giao diện
tree.pack(expand=True, fill="both")

# Lắng nghe sự kiện chọn dòng
tree.bind("<<TreeviewSelect>>", on_select)

# Tạo các Entry tìm kiếm tương ứng với từng cột
search_entries = []
for i, col in enumerate(columns):
    entry = tk.Entry(search_frame, width=column_widths[i] // 8)
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
frame_inner.pack(expand=True)

# Nút Cập nhật dòng
btn_update = tk.Button(frame_inner, text="Cập nhật dòng",
                       command=update_selected)
btn_update.pack(side="left", padx=5, pady=5)

# Nút Xóa dòng
btn_delete = tk.Button(frame_inner, text="Xóa dòng", command=delete_selected,
                       fg="red")
btn_delete.pack(side="left", padx=5, pady=5)

# Nút Lưu file M3U
btn_save = tk.Button(frame_inner, text="Lưu danh sách M3U", command=save_m3u)
btn_save.pack(side="left", padx=5, pady=5)

# Nút Tải lại danh sách
btn_reload = tk.Button(frame_inner, text="Tải lại danh sách",
                       command=reload_data, fg="blue")
btn_reload.pack(side="left", padx=5, pady=5)

# Nút Play kênh đã chọn
btn_play = tk.Button(frame_inner, text="Phát kênh", command=play_selected_channel, fg="green")
btn_play.pack(side="left", padx=5, pady=5)

# Nút kiểm tra chất lượng kênh
btn_check = tk.Button(frame_inner, text="Kiểm tra kênh", command=check_channel_quality, fg="purple")
btn_check.pack(side="left", padx=5, pady=5)

# Load danh sách IPTV ban đầu
if iptv_url:
    channels = load_iptv_list(iptv_url)
else:
    channels = []

if not channels:
    channels = []

# Hiển thị danh sách kênh ban đầu
display_channels()

# Sau khi hiển thị, kiểm tra trạng thái từng kênh (có thể tốn thời gian)
for item in tree.get_children():
    url = tree.item(item)["values"][6]
    thread = threading.Thread(target=check_url_status_and_color, args=(item, url))
    thread.start()

root.mainloop()