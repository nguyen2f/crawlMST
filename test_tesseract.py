import cv2
import pytesseract
from PIL import Image
import numpy as np
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# --- PHẦN CẤU HÌNH ---
# ==============================================================================

# 1. Đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 2. URL của trang web
URL_TRACUU = "https://tracuunnt.gdt.gov.vn/tcnnt/mstcn.jsp"

# 3. Chế độ debug: True để hiển thị các bước xử lý ảnh
DEBUG_MODE = True


# ==============================================================================
# --- HÀM XỬ LÝ ẢNH VÀ OCR (Giữ nguyên) ---
# ==============================================================================
# (Bạn có thể dán lại hàm solve_captcha chi tiết từ các câu trả lời trước ở đây)
def process_and_solve(image_path):
    # ... (Toàn bộ code của hàm xử lý ảnh như trước)
    try:
        original_img = cv2.imread(image_path)
        if original_img is None:
            print(f"Lỗi: Không thể đọc được file ảnh tại '{image_path}'")
            return

        if DEBUG_MODE: cv2.imshow("1. Anh Goc Selenium Chup", original_img); cv2.waitKey(0)

        gray_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        thresh_img = cv2.adaptiveThreshold(gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 17, 9)

        if DEBUG_MODE: cv2.imshow("2. Anh Nhi Phan Hoa (Thresh)", thresh_img); cv2.waitKey(0)

        contours, _ = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(gray_img)
        letter_contours = [c for c in contours if 5 < cv2.boundingRect(c)[2] < 40 and 15 < cv2.boundingRect(c)[3] < 45]
        cv2.drawContours(mask, letter_contours, -1, (255), -1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        final_image = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        cv2.imwrite('test_processed.png', final_image)

        if DEBUG_MODE:
            cv2.imshow("3. Anh Cuoi Cung Dua Cho Tesseract", final_image);
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        print("\n--- KET QUA TU TESSERACT ---")
        for psm_mode in ['7', '8', '13', '6', '10']:
            custom_config = f'--oem 3 --psm {psm_mode} -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789'
            text = pytesseract.image_to_string(final_image, config=custom_config)
            solved_text = "".join(filter(str.isalnum, text)).lower()
            print(f"Voi psm='{psm_mode}': '{solved_text}' (do dai: {len(solved_text)})")
    except Exception as e:
        print(f"!!! Xảy ra lỗi: {e}")


# ==============================================================================
# --- HÀM CHÍNH ĐỂ CHẠY THỬ NGHIỆM ---
# ==============================================================================
def run_test():
    """
    Mở trình duyệt, chụp ảnh CAPTCHA và gọi hàm xử lý.
    """
    options = webdriver.ChromeOptions()
    # Giữ trình duyệt mở sau khi script chạy xong để tiện kiểm tra
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    try:
        print("-> Đang mở trình duyệt và truy cập trang web...")
        driver.get(URL_TRACUU)

        # Locator để tìm ảnh CAPTCHA
        CAPTCHA_IMAGE_LOCATOR = (By.CSS_SELECTOR, "img[src*='captcha.png']")

        # Chờ cho ảnh xuất hiện
        WebDriverWait(driver, 10).until(EC.presence_of_element_located(CAPTCHA_IMAGE_LOCATOR))

        # Tìm đúng phần tử ảnh
        captcha_element = driver.find_element(*CAPTCHA_IMAGE_LOCATOR)
        print("-> Đã tìm thấy phần tử ảnh CAPTCHA trên trang.")

        # Chụp màn hình của chỉ riêng phần tử này
        captcha_path = 'captcha_live_screenshot.png'
        captcha_element.screenshot(captcha_path)
        print(f"-> Đã chụp ảnh CAPTCHA trực tiếp từ trình duyệt và lưu vào '{captcha_path}'")

        # Đóng trình duyệt sau khi chụp xong để tiết kiệm tài nguyên
        driver.quit()

        # Bây giờ, gọi hàm xử lý với tấm ảnh vừa chụp được
        print("\n--- BAT DAU XU LY ANH VUA CHUP ---")
        process_and_solve(captcha_path)

    except Exception as e:
        print(f"!!! Lỗi khi chạy Selenium: {e}")
        if 'driver' in locals():
            driver.quit()


if __name__ == "__main__":
    run_test()