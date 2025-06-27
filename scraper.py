# --- 1. IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import time
import cv2
import pytesseract
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from PIL import Image

# ==============================================================================
# --- 2. PHẦN CẤU HÌNH ---
# ==============================================================================

# QUAN TRỌNG: Đường dẫn đến file thực thi của Tesseract OCR trên máy bạn.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# URL của trang web tra cứu
URL_TRACUU = "https://tracuunnt.gdt.gov.vn/tcnnt/mstcn.jsp"

# Danh sách mã số thuế hoặc CCCD bạn muốn tra cứu
LIST_IDS = [
    "010204002990",
    "010204002991",
    "010204002992"
]

# Tên file CSV để lưu kết quả
OUTPUT_CSV_FILE = 'ket_qua_tra_cuu.csv'


# ==============================================================================
# --- 3. HÀM GIẢI MÃ CAPTCHA ---
# (Sử dụng phương pháp phân đoạn ký tự để tăng độ chính xác)
# ==============================================================================

def solve_captcha(image_path):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 17, 9)

        # Phương pháp 1: Phân đoạn ký tự
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        MIN_WIDTH, MAX_WIDTH = 5, 40
        MIN_HEIGHT, MAX_HEIGHT = 15, 45
        letter_contours = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if (MIN_WIDTH < w < MAX_WIDTH) and (MIN_HEIGHT < h < MAX_HEIGHT):
                letter_contours.append(c)

        if len(letter_contours) == 5:
            letter_contours = sorted(letter_contours, key=lambda c: cv2.boundingRect(c)[0])
            recognized_text = ""
            for contour in letter_contours:
                x, y, w, h = cv2.boundingRect(contour)
                char_image = thresh[y:y + h, x:x + w]
                padded_char = cv2.copyMakeBorder(char_image, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=[0])
                custom_config = r'--oem 3 --psm 10 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789'
                char = pytesseract.image_to_string(padded_char, config=custom_config)
                clean_char = "".join(filter(str.isalnum, char)).lower()
                if clean_char:
                    recognized_text += clean_char[0]

            if len(recognized_text) == 5:
                return recognized_text

        # Phương pháp 2: Xử lý toàn ảnh nếu phương pháp 1 thất bại
        mask = np.zeros_like(thresh)
        cv2.drawContours(mask, letter_contours, -1, (255), -1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        cv2.imwrite('captcha_processed.png', mask)

        for psm_mode in ['7', '8', '13']:
            custom_config = f'--oem 3 --psm {psm_mode} -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789'
            text = pytesseract.image_to_string(mask, config=custom_config)
            solved_text = "".join(filter(str.isalnum, text)).lower()
            if len(solved_text) == 5:
                return solved_text

        return None
    except Exception as e:
        print(f"!!! Lỗi nghiêm trọng trong hàm solve_captcha: {e}")
        return None


# ==============================================================================
# --- 4. HÀM CHÍNH ĐỂ CÀO DỮ LIỆU ---
# ==============================================================================

def main():
    all_results = []
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    # --- Định nghĩa các "Locator" để tìm phần tử trên trang ---
    # Locator cho ô nhập CCCD/MST (tìm theo thuộc tính 'name')
    ID_INPUT_LOCATOR = (By.NAME, "cmt")
    # Locator cho ô nhập CAPTCHA (tìm theo 'id')
    CAPTCHA_INPUT_LOCATOR = (By.ID, "captcha")
    # Locator cho nút "Tra cứu" (tìm theo 'class')
    SUBMIT_BUTTON_LOCATOR = (By.CLASS_NAME, "subBtn")

    # === LOCATOR CHO ẢNH CAPTCHA KHÔNG CÓ ID ===
    # Tìm thẻ <img> có thuộc tính 'src' chứa chuỗi "captcha.png".
    # Đây là cách tìm chính xác và đáng tin cậy cho trường hợp này.
    CAPTCHA_IMAGE_LOCATOR = (By.CSS_SELECTOR, "img[src*='captcha.png']")

    # Locator cho thẻ DIV chứa kết quả
    RESULT_CONTAINER_LOCATOR = (By.ID, "resultContainer")

    try:
        for search_id in LIST_IDS:
            print(f"\n{'=' * 30}\nĐang tra cứu cho ID: {search_id}\n{'=' * 30}")
            for attempt in range(2):  # Thử lại tối đa 2 lần nếu thất bại
                try:
                    driver.get(URL_TRACUU)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located(ID_INPUT_LOCATOR))

                    # 1. TÌM VÀ CHỤP ĐÚNG ẢNH CAPTCHA
                    captcha_element = driver.find_element(*CAPTCHA_IMAGE_LOCATOR)
                    captcha_path = 'captcha_screenshot.png'
                    captcha_element.screenshot(captcha_path)
                    print(f"-> Đã tìm và chụp thành công ảnh CAPTCHA.")

                    # 2. GIẢI MÃ ẢNH ĐÃ CHỤP
                    captcha_code = solve_captcha(captcha_path)
                    if not captcha_code:
                        print(f"-> Lần thử {attempt + 1}: Giải mã thất bại. Thử lại...")
                        time.sleep(2)
                        continue

                    print(f"-> Kết quả giải mã: '{captcha_code}'")

                    # 3. ĐIỀN THÔNG TIN VÀ SUBMIT
                    driver.find_element(*ID_INPUT_LOCATOR).send_keys(search_id)
                    driver.find_element(*CAPTCHA_INPUT_LOCATOR).send_keys(captcha_code)
                    driver.find_element(*SUBMIT_BUTTON_LOCATOR).click()
                    print("-> Đã nhấn nút tra cứu. Đang chờ kết quả...")

                    # 4. CHỜ VÀ TRÍCH XUẤT KẾT QUẢ
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located(RESULT_CONTAINER_LOCATOR))
                    print("-> Vùng kết quả đã xuất hiện!")

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    result_div = soup.find('div', id='resultContainer')

                    if result_div and (table := result_div.find('table', class_='ta_border')):
                        rows = table.find_all('tr')
                        for row in rows[1:]:
                            cols = [ele.text.strip() for ele in row.find_all('td')]
                            all_results.append([search_id] + cols)
                        print(f"==> THÀNH CÔNG! Đã trích xuất {len(rows) - 1} dòng dữ liệu.")
                        break  # Thoát khỏi vòng lặp thử lại vì đã thành công
                    else:
                        raise Exception("Không tìm thấy bảng kết quả bên trong div 'resultContainer'.")

                except Exception as e:
                    print(f"!!! Lần thử {attempt + 1} thất bại: {e}")
                    if attempt < 1:
                        time.sleep(3)
                    else:
                        print(f"-> Đã hết lượt thử cho ID {search_id}. Bỏ qua.")
                        driver.save_screenshot(f'error_screenshot_{search_id}.png')

            time.sleep(2)

    finally:
        print("\n" + "=" * 30 + "\nScript đã chạy xong.\n" + "=" * 30)

    # --- 5. LƯU KẾT QUẢ RA FILE CSV ---
    if all_results:
        columns = ['ID_TimKiem', 'STT', 'MST', 'Tên người nộp thuế', 'Cơ quan thuế', 'Số CMT/Thẻ căn cước',
                   'Ngày thay đổi thông tin gần nhất', 'Ghi chú']
        df = pd.DataFrame(all_results, columns=columns)
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"\nHoàn tất! Đã lưu {len(all_results)} kết quả vào file '{OUTPUT_CSV_FILE}'.")
    else:
        print("\nKhông có dữ liệu nào được cào thành công để lưu.")


# ==============================================================================
# --- 6. GỌI HÀM CHÍNH ĐỂ BẮT ĐẦU ---
# ==============================================================================
if __name__ == "__main__":
    main()