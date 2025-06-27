# --- 1. IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

URL_TRACUU = "https://masothue.com/"

LIST_IDS = [
    "010204002990",
    "010204002991",
    "010204002993"
]

OUTPUT_CSV_FILE = 'masothue_khachhang.csv'

def main():
    all_results = []

    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    try:
        for search_id in LIST_IDS:
            print(f"\n{'=' * 30}\nĐang tra cứu cho ID: {search_id}\n{'=' * 30}")

            try:
                driver.get(URL_TRACUU)
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
                search_input.clear()  # Xóa nội dung cũ (nếu có)
                search_input.send_keys(search_id)
                print(f"-> Đã điền ID '{search_id}' vào ô tìm kiếm.")

                submit_button = driver.find_element(By.CSS_SELECTOR, "button.btn-search-submit")
                submit_button.click()
                print("-> Đã nhấn nút tìm kiếm.")

                print("-> Đang chờ trang tải kết quả...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "table-taxinfo"))
                )
                print("-> Bảng thông tin đã xuất hiện!")

                time.sleep(1)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                main_header = soup.find('h1')
                ten_chinh = main_header.text.strip() if main_header else "Không tìm thấy tên"

                table = soup.find('table', class_='table-taxinfo')

                if table:
                    company_info = {'ID_TimKiem': search_id, 'Tên người nộp thuế': ten_chinh}
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            field_name = cols[0].text.strip()
                            value = cols[1].text.strip()
                            company_info[field_name] = value

                    all_results.append(company_info)
                    print(f"==> THÀNH CÔNG! Đã trích xuất thông tin cho '{ten_chinh}'.")
                else:
                    print("-> Lỗi! Không tìm thấy bảng thông tin trên trang kết quả.")

            except Exception as e:
                print(f"!!! Lỗi khi xử lý ID {search_id}: {type(e).__name__} - {e}")
                driver.save_screenshot(f'error_masothue_{search_id}.png')
                print(f"-> Đã lưu ảnh màn hình lỗi vào 'error_masothue_{search_id}.png'.")
                continue  # Bỏ qua ID này và tiếp tục với ID tiếp theo

            time.sleep(2)

    finally:
        print("\n" + "=" * 30 + "\nScript đã chạy xong.\n" + "=" * 30)
        driver.quit()  # Đóng trình duyệt khi hoàn tất

    if all_results:
        df = pd.DataFrame(all_results)

        # Sắp xếp lại các cột cho đẹp (tùy chọn)
        desired_columns = [
            'ID_TimKiem',
            'Tên người nộp thuế',
            'Mã số thuế cá nhân',
            'Địa chỉ'
        ]
        df = df.reindex(columns=[col for col in desired_columns if col in df.columns])

        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"\nHoàn tất! Đã lưu {len(all_results)} kết quả vào file '{OUTPUT_CSV_FILE}'.")
    else:
        print("\nKhông có dữ liệu nào được cào thành công để lưu.")

if __name__ == "__main__":
    main()