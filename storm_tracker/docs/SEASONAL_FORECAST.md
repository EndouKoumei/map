# dự báo mùa - Dự Báo Xác Suất Mùa Bão 2026

Phần dự báo mùa bổ sung hướng "dự báo tương lai" cho đồ án. Đây là model thống kê đơn giản, dùng để demo năng lực phân tích theo mùa, không phải dự báo khí tượng chính thức.

## Dữ Liệu

- Lịch sử bão: `data/storms_vn.geojson`, sinh từ IBTrACS/NOAA.
- Kịch bản ENSO/SST 2026: `data/climate_scenario_2026.csv`.
- ENSO 2026: dựa trên NOAA CPC ENSO Diagnostic Discussion ngày 2026-06-11, trạng thái El Niño Advisory.
- SST: các cột `sst_scs_anom_c` và `sst_phil_anom_c` là input scenario. Bản đầu để trống/neutral; có thể thay bằng số trung bình vùng từ OISST hoặc NMME khi tải được.

## Output

API:

```text
GET /api/seasonal-forecast?year=2026
```

Trang:

```text
/seasonal-forecast
```

Mỗi tháng trả:

- số cơn bão kỳ vọng;
- xác suất có 0, 1, 2, hoặc 3+ cơn;
- xác suất vùng hình thành: Biển Đông, vùng biển Philippines, Tây Bắc Thái Bình Dương khác;
- xác suất vùng ảnh hưởng gần Việt Nam: Bắc Bộ, Trung Bộ, Nam Bộ, không vào vùng ven biển VN;
- feature khí hậu của tháng đó: ENSO phase, ONI, SST anomaly scenario.

## Cách Model Hoạt Động

1. Tạo bảng lịch sử theo `year-month` từ IBTrACS giai đoạn 1981-2025.
2. Tính climatology theo tháng: số cơn trung bình, phân bố vùng hình thành, phân bố vùng ảnh hưởng.
3. Đọc kịch bản ENSO/SST năm 2026 từ CSV.
4. Điều chỉnh climatology bằng hệ số ENSO và SST:
   - El Niño làm dịch xác suất hình thành về phía vùng biển Philippines nhiều hơn;
   - SST anomaly cao làm tăng nhẹ số cơn kỳ vọng;
   - xác suất vào vùng ven biển VN được điều chỉnh thận trọng trong kịch bản El Niño.
5. Chuyển số cơn kỳ vọng sang xác suất 0/1/2/3+ bằng phân phối Poisson.

## Giới Hạn Cần Ghi Trong Báo Cáo

- Model này là outlook xác suất theo mùa, không dự báo đường đi từng cơn.
- SST hiện là input scenario CSV; nếu muốn chặt chẽ hơn cần thay bằng OISST/NMME thật.
- Vùng ảnh hưởng Bắc/Trung/Nam là xấp xỉ theo điểm track gần vùng biển Việt Nam, chưa phải landfall theo đường bờ.
- Kết quả phù hợp để demo định hướng tương lai của hệ thống, không dùng thay thế bản tin dự báo chính thức.
