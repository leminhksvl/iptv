import requests
import gzip
import xml.etree.ElementTree as ET
import openpyxl

# Đọc danh sách URL từ file epgUrl.txt
with open("epgUrl.txt", "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f.readlines() if line.strip()]

# Tạo file Excel và thêm tiêu đề cột
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "EPG Data"
ws.append(["URL", "Channel ID", "Display Name", "Icon Src"])

# Xử lý từng URL
for url in urls:
    print(f"Đang xử lý: {url}")

    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            # Giải nén file XML ngay từ response
            with gzip.GzipFile(fileobj=response.raw) as f:
                xml_data = f.read()

            # Parse XML
            root = ET.fromstring(xml_data)

            # Duyệt qua các kênh
            for channel in root.findall("channel"):
                channel_id = channel.get("id", "N/A")
                display_name = channel.find("display-name").text if channel.find("display-name") is not None else "N/A"
                icon = channel.find("icon").get("src") if channel.find("icon") is not None else "N/A"

                # Ghi dữ liệu vào Excel
                ws.append([url, channel_id, display_name, icon])
        
        else:
            print(f"Lỗi {response.status_code} khi tải: {url}")

    except Exception as e:
        print(f"Lỗi khi xử lý {url}: {e}")

# Lưu file Excel
excel_path = "epg.xlsx"
wb.save(excel_path)
print(f"Dữ liệu đã được lưu vào {excel_path}")