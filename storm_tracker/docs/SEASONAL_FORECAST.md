# Outlook Xac Suat Mua Bao 2026

Trang `/seasonal-forecast` la outlook thong ke theo thang cho mua bao 2026. Muc
dich la minh hoa huong phat trien du bao theo mua cua he thong, khong phai du bao
khi tuong nghiep vu hay du bao tung con bao.

## Du Lieu Dau Vao

- Lich su: `data/storms_vn.geojson`, xu ly tu IBTrACS/NOAA.
- Mau huan luyen: cac thang trong giai doan 1981-2025.
- Kich ban khi hau: `data/climate_scenario_2026.csv`.

CSV khi hau luu trang thai ENSO, ONI va bat thuong SST cho tung thang. Truoc khi
demo hoac dua vao bao cao, can kiem tra lai ngay phat hanh va nguon cua kich ban.
Neu cac truong SST de trong, model xem bat thuong SST bang 0 va khong tao dieu
chinh tu SST.

## Cac Chi So Tren Trang

| Thanh phan | Cach dien giai |
| --- | --- |
| Tong so con ky vong ca nam | Tong gia tri trung binh thong ke cua 12 thang, khong phai so bao chac chan xay ra. |
| Thang rui ro cao nhat | Thang co so con ky vong lon nhat trong model. |
| Thang co kich ban El Nino | So dong thang trong CSV duoc gan pha El Nino. |
| So con ky vong theo thang | Trung binh so he thong trong pham vi tap du lieu cua thang do. |
| Xac suat 0, 1, 2, 3+ con | Phan bo Poisson duoc tinh tu so con ky vong. |
| Vung hinh thanh chinh | Vung co xac suat lon nhat trong Bien Dong, vung bien Philippines, hoac Tay Bac Thai Binh Duong khac. |
| Vung anh huong chinh | Vung co xac suat lon nhat trong Bac Bo, Trung Bo, Nam Bo, hoac khong vao vung ven bien Viet Nam. |

Hai bieu do vung chi ve xac suat cua **vung dung dau** moi thang. Ten vung hien
trong tooltip; chung khong the hien day du phan bo cua tat ca vung tren cung mot
bieu do.

## Cach Model Hoat Dong

1. Gom bao theo nam-thang tu quy dao lich su 1981-2025.
2. Tinh trung binh so bao va phan bo vung hinh thanh/anh huong cho tung thang.
3. Doc kich ban ENSO/SST cua 2026 tu CSV.
4. Dieu chinh nhe climatology: kich ban El Nino tang trong so vung Philippines,
   giam nhe Bien Dong va giam nhe trong so mot so vung gan Viet Nam. SST chi tac
   dong khi cac cot bat thuong SST co gia tri.
5. Chuyen so con ky vong thanh xac suat 0, 1, 2 va 3+ con bang phan bo Poisson.

`very_strong_el_nino_probability` hien la metadata cua kich ban de tham khao; no
chua duoc dung truc tiep de thay doi ket qua model.

## Pham Vi Thoi Gian

API hien tra ve 12 thang cua nam 2026 va KPI tong cong ca 12 thang. Khi xem trong
nam 2026, cac thang da qua la phan climatology hien thi, khong phai du bao tuong
lai. Vi vay, khi trinh bay "phan con lai cua mua", chi nen dien giai cac thang sau
thoi diem hien tai.

## Gioi Han

- Ket qua la xac suat trung binh, khong phai so bao se xay ra chinh xac.
- Khong du bao toa do hinh thanh, duong di, cuong do hay ngay gio cua tung bao.
- "Vung anh huong" duoc suy ra tu cac diem quy dao trong mot khung toa do gan Viet
  Nam; day khong phai phep tinh giao cat duong bo va khong phai thong ke theo tinh.
- Ket qua phu thuoc vao pham vi tap du lieu lich su va kich ban ENSO/SST trong CSV.
- Khong dung ket qua thay cho canh bao hay ban tin cua co quan khi tuong.

## API

```text
GET /api/seasonal-forecast?year=2026
```

Moi thang tra ve `expected_storms`, `count_probabilities`,
`genesis_region_probabilities`, `landfall_region_probabilities` va `climate`.
