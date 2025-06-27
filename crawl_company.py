import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

URL_TRACUU = "https://masothue.com/"

LIST_IDS = [
    "0107973996",  # Mã số thuế công ty
    "0300588569"  # Thêm các mã số khác
]

OUTPUT_CSV_FILE = 'masothue_doanhnghiep.csv'

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
                search_input.clear()
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
                ten_chinh = main_header.text.strip().replace(f"{search_id} - ",
                                                             "") if main_header else "Không tìm thấy tên"

                table = soup.find('table', class_='table-taxinfo')

                if table:
                    record_info = {
                        'ID_TimKiem': search_id,
                        'Tên chính': ten_chinh
                    }
                    # Lặp qua từng hàng <tr> trong bảng
                    for row in table.find_all('tr'):
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            field_name = cols[0].text.strip()

                            # Lấy thẻ <td> chứa giá trị
                            value_cell = cols[1]

                            # Mặc định, lấy giá trị từ text
                            value = value_cell.text.strip()

                            if "Địa chỉ" in field_name:
                                # Ưu tiên lấy dữ liệu từ thuộc tính 'title' nếu nó tồn tại
                                if value_cell.has_attr('title') and value_cell['title']:
                                    value = value_cell['title'].strip()
                                    print("-> Tìm thấy và đã lấy địa chỉ đầy đủ từ thuộc tính 'title'.")

                            if "Điện thoại" in field_name and "Ẩn thông tin" in value:
                                value = value.replace("Ẩn thông tin", "").strip()

                            record_info[field_name] = value

                    all_results.append(record_info)
                    print(f"==> THÀNH CÔNG! Đã trích xuất thông tin cho: '{ten_chinh}'.")
                else:
                    print("-> Lỗi! Không tìm thấy bảng thông tin trên trang kết quả.")

            except Exception as e:
                print(f"!!! Lỗi khi xử lý ID {search_id}: {type(e).__name__}")
                driver.save_screenshot(f'error_masothue_{search_id}.png')
                print(f"-> Đã lưu ảnh màn hình lỗi vào 'error_masothue_{search_id}.png'.")
                continue

            time.sleep(2)

    finally:
        print("\n" + "=" * 30 + "\nScript đã chạy xong.\n" + "=" * 30)
        driver.quit()

    if all_results:
        full_df = pd.DataFrame(all_results)
        print("\n--- Các cột dữ liệu đã cào được ---")
        print(list(full_df.columns))
        print("------------------------------------")
        desired_columns = [
            'ID_TimKiem',
            'Tên chính',
            'Tên quốc tế',
            'Mã số thuế',
            'Địa chỉ',
        ]

        columns_to_keep = [col for col in desired_columns if col in full_df.columns]

        final_df = full_df[columns_to_keep]

        # encoding='utf-8-sig' để Excel mở không bị lỗi font tiếng Việt
        final_df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')

        print(f"\nHoàn tất! Đã lưu {len(final_df)} kết quả với các cột đã chọn vào file '{OUTPUT_CSV_FILE}'.")
    else:
        print("\nKhông có dữ liệu nào được cào thành công để lưu.")

if __name__ == "__main__":
    main()