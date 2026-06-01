# Hướng dẫn chạy ứng dụng Định giá iPhone

Để chạy ứng dụng Streamlit bạn vừa tạo, hãy làm theo các bước sau:

### 1. Cài đặt thư viện cần thiết
Nếu bạn chưa cài đặt các thư viện liên quan, hãy chạy lệnh sau trong terminal:

```bash
pip install -r requirements.txt
```

### 2. Chạy ứng dụng
Mở terminal tại thư mục dự án (`d:\CDIO\cao_du_lieu_ien_thoai_iphon_2\cao_du_lieu_ien_thoai_iphon\`) và chạy lệnh:

```bash
streamlit run app.py
```

### 3. Truy cập giao diện
Sau khi chạy lệnh trên, Streamlit sẽ cung cấp một địa chỉ Local URL (thường là `http://localhost:8501`). Hãy mở trình duyệt và truy cập vào địa chỉ đó để trải nghiệm giao diện định giá iPhone chuyên nghiệp.

---
**Lưu ý:** Đảm bảo file model `xgboost_best_model.pkl` nằm đúng trong thư mục `output/` như cấu trúc hiện tại.
