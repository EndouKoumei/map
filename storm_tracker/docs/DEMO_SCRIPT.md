# Kich Ban Demo 10-15 Phut

## 0. Chuan Bi

- Chay local: `python app.py`.
- Mo san 4 tab: `/`, `/realtime`, `/dashboard`, `/api/status`.
- Neu internet loi, dung fallback Yagi 2024 o M2.

## 1. Gioi Thieu He Thong (1 phut)

Noi ngan gon:

- De tai xay dung WebGIS theo doi, phan tich va so sanh bao anh huong den vung bien Viet Nam.
- Du lieu lich su tu IBTrACS/NOAA, du lieu gan thoi gian thuc tu JMA/IBTrACS NRT, fallback Yagi 2024 de dam bao demo.
- He thong gom M1 lich su, M2 realtime, M3 similarity, M4 dashboard.

## 2. M1 - Ban Do Lich Su (3 phut)

Thao tac:

- Mo `/`.
- Loc nam 1960-2026, chon tat ca cap bao.
- Chuyen Track/Heatmap/Thong ke.
- Click vao mot duong di bao.

Diem can noi:

- Track co gradient theo cuong do tung doan, dung phan cap Viet Nam.
- Khi chon mot bao, cac bao khac duoc an de quan sat ro hon.
- Co animation phat lai duong di.

## 3. M3 - Tim Bao Tuong Tu (2 phut)

Thao tac:

- Tu panel bao dang chon, bam `Tim bao lich su tuong tu (M3)`.
- Giai thich bang top-5.

Diem can noi:

- DTW so sanh hinh dang/quy dao theo chuoi toa do.
- Cosine/multi-factor bo sung huong di, centroid, thang mua bao, gio cuc dai.
- `combined_score` giup xep hang tong hop.

## 4. M2 - Theo Doi Thoi Gian Thuc (3 phut)

Thao tac:

- Mo `/realtime`.
- Bam Lam moi.
- Click bao Yagi mau hoac bao that neu co.
- Mo du bao duong di neu co.

Diem can noi:

- API luon tra JSON hop le.
- Khi JMA/IBTrACS khong co bao hoac loi, he thong fallback sang Yagi 2024.
- Muc tieu la he thong khong chet im lang khi nguon du lieu ngoai bat on.

## 5. M4 - Dashboard Phan Tich (3 phut)

Thao tac:

- Mo `/dashboard`.
- Chi vao KPI tong 2,343 bao, 1884-2026, max 170 kt.
- Mo bieu do thang, thap ky, phan cap, vung.

Diem can noi:

- Mua bao tap trung manh tu thang 7 den thang 10, dinh la thang 9.
- Sau nam 2000, ti le sieu bao trong tap du lieu cao hon giai doan truoc 2000.
- Phan vung Bac/Trung/Nam la xap xi theo toa do, khong thay the thong ke do bo theo tinh.

## 6. Ket Thuc (1 phut)

Tong ket:

- He thong dap ung truc quan hoa lich su, theo doi gan thoi gian thuc, so sanh quy dao va dashboard phan tich.
- Huong phat trien: bo sung canh bao vung ven bien Viet Nam, du bao cone bat dinh, thong ke do bo theo tinh chinh xac hon.

## Phuong An Du Phong

- Neu internet loi: demo local va fallback Yagi.
- Neu nguon realtime khong co bao: giai thich day la thiet ke fallback de demo on dinh.
