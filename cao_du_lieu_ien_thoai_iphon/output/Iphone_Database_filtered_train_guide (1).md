# Hướng dẫn nhanh cho file `Iphone_Database_filtered_train.csv`

## 1. Mục đích file

File `CleanData/clean_outputs/Iphone_Database_filtered_train.csv` là dataset đã được làm sạch để train model dự đoán **giá iPhone cũ**.

- Số dòng: `1070`
- Số cột: `10`
- Không có ô trống ở các cột hiện tại
- Biến mục tiêu cần dự đoán: `Giá`

## 2. Các cột trong dataset

| Cột | Ý nghĩa | Gợi ý dùng khi train |
|---|---|---|
| `Dòng máy` | Tên model iPhone | Dùng làm feature |
| `Giá` | Giá bán của máy | Đây là `target` |
| `Phiên bản` | Quốc tế / Lock | Dùng làm feature |
| `Tình trạng` | Mới / đã sử dụng / đã sửa chữa | Dùng làm feature |
| `Tinh_trang_tong_hop` | Tình trạng tổng hợp sau khi làm sạch, ví dụ `Zin không trầy xước`, `Pin thay` | Dùng làm feature |
| `Xuất xứ` | Ví dụ `VN/A`, `Mỹ (LL/A)` | Dùng làm feature |
| `Dung lượng (GB)` | Bộ nhớ máy | Dùng làm feature số |
| `Tình trạng pin` | Ví dụ `84%`, `100%` | Cột tham khảo, không dùng trong baseline |
| `Pin_bucket` | Nhóm pin, ví dụ `97-99%`, `100%` | Dùng làm feature khi train |
| `Chính sách bảo hành` | Tình trạng bảo hành | Dùng làm feature |

## 3. Gợi ý train baseline

Để train nhanh và ổn định với XGBoost, nên dùng:

- `Giá` làm biến cần dự đoán
- `Dung lượng (GB)` là cột số
- Các cột còn lại encode dạng category
- Dùng `Pin_bucket` để biểu diễn tình trạng pin khi train

Thiết lập baseline được khuyến nghị:

- Giữ `Pin_bucket`
- Bỏ `Tình trạng pin`

Lý do là `Pin_bucket` đã gom nhóm pin theo các khoảng dễ học hơn, đồng thời tránh trùng thông tin với `Tình trạng pin`.

## 4. Ví dụ train bằng Python + XGBoost

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

# 1. Đọc dữ liệu
df = pd.read_csv("CleanData/clean_outputs/Iphone_Database_filtered_train.csv")

# 2. Chọn feature và target
# Baseline: dùng Pin_bucket để train, bỏ Tình trạng pin
X = df.drop(columns=["Giá", "Tình trạng pin"])
y = df["Giá"]

# 3. Khai báo cột
numeric_features = ["Dung lượng (GB)"]
categorical_features = [col for col in X.columns if col not in numeric_features]

# 4. Preprocess
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ("num", "passthrough", numeric_features),
    ]
)

# 5. Model
model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
)

# 6. Pipeline
pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", model)
])

# 7. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 8. Train
pipeline.fit(X_train, y_train)

# 9. Evaluate
pred = pipeline.predict(X_test)
mae = mean_absolute_error(y_test, pred)
rmse = mean_squared_error(y_test, pred) ** 0.5

print("MAE:", mae)
print("RMSE:", rmse)
```

## 5. Dạng input khi predict

Khi người dùng nhập thông tin để dự đoán giá, input nên có cùng cấu trúc như các feature lúc train. Ví dụ:

```python
sample = pd.DataFrame([{
    "Dòng máy": "iPhone 14 Pro Max",
    "Phiên bản": "Quốc tế (Không khoá mạng)",
    "Tình trạng": "Đã sử dụng (chưa sửa chữa)",
    "Tinh_trang_tong_hop": "Zin không trầy xước",
    "Xuất xứ": "VN/A",
    "Dung lượng (GB)": 256,
    "Pin_bucket": "97-99%",
    "Chính sách bảo hành": "Hết bảo hành"
}])

predicted_price = pipeline.predict(sample)
print(predicted_price)
```

## 6. Lưu ý

- `Giá` đang là giá số nguyên, đơn vị VND
- `Dung lượng (GB)` là cột số, hiện có các mức như `64`, `128`, `256`, `512`, `1024`, `2048`
- Dataset này phù hợp để train bài toán **regression**
- Nên đánh giá thêm bằng `MAE`, vì dễ hiểu hơn với bài toán dự đoán giá
- Nếu muốn model tốt hơn, có thể thử `KFold cross-validation`, tuning tham số XGBoost, hoặc gom nhóm hiếm ở các cột category

## 7. Kết luận ngắn

Nếu cần train nhanh:

1. Đọc file CSV
2. Dùng `Giá` làm target
3. Giữ `Dung lượng (GB)` là số
4. One-hot encode các cột category
5. Dùng `Pin_bucket` cho baseline đầu tiên
6. Train `XGBRegressor`
