# Kich Ban Demo 10-15 Phut

## Chuan Bi

- Chay `python app.py`.
- Mo san: `/`, `/realtime`, `/dashboard`, `/seasonal-forecast` va `/api/status`.
- Neu nguon realtime loi, dung fallback Yagi 2024 de tiep tuc demo.

## Gioi Thieu (1 Phut)

Gioi thieu Storm Tracker VN la WebGIS ho tro tra cuu lich su, theo doi gan thoi
gian thuc, so sanh quy dao, phan tich thong ke va outlook xac suat mua bao.

## Ban Do Lich Su (3 Phut)

1. Mo `/`, loc nam 1960-2026 va chuyen Track/Heatmap/Thong ke.
2. Chon mot duong di bao bat ky.
3. Chi ra quy dao gradient theo cuong do, animation va panel chi tiet.
4. Dong panel de hien lai toan bo quy dao.

Nhan manh: khi chon mot bao, cac bao khac an di de quan sat ro hon; nhan vao bat
ky doan nao cua quy dao deu co the mo thong tin bao.

## Tim Bao Tuong Tu (2 Phut)

1. Tu panel bao da chon, bam `Tim bao lich su tuong tu`.
2. Mo bang top-5 va cac quy dao so sanh.

Nhan manh: DTW so sanh hinh dang quy dao; diem tong hop bo sung huong di,
centroid, thang mua bao va gio cuc dai.

## Theo Doi Thoi Gian Thuc (3 Phut)

1. Mo `/realtime` va bam lam moi.
2. Chon bao dang co hoac Yagi mau khi nguon ngoai khong san sang.
3. Mo panel thong tin va quy dao du bao neu nguon co cung cap.

Nhan manh: fallback giup trang van hoat dong khi JMA/IBTrACS khong phan hoi. Neu
JMA khong cung cap gio hoac ap suat, giao dien hien thi trang thai chua co so lieu.

## Dashboard Phan Tich (2 Phut)

1. Mo `/dashboard`.
2. Chi vao KPI tong so bao, khoang nam du lieu va gio lon nhat.
3. Mo bieu do theo thang, thap ky, phan cap va vung.

Nhan manh: phan vung Bac/Trung/Nam la xap xi theo toa do quy dao, khong thay the
thong ke do bo theo tinh.

## Outlook Mua Bao (2 Phut)

1. Mo `/seasonal-forecast`.
2. Chi vao so con ky vong theo thang, phan bo 0/1/2/3+ con va bang outlook.
3. Giai thich vung hinh thanh/anh huong chinh va kich ban ENSO.

Nhan manh: day la outlook xac suat tu climatology 1981-2025 va kich ban khi hau.
No khong du bao tung con bao, khong thay the ban tin chinh thuc. Khi trinh bay giua
nam 2026, chi dien giai cac thang chua qua; cot SST trong nghia la chua co dieu
chinh SST thuc te.

## Phuong An Du Phong

- Neu Railway bao loi, kiem tra `/api/status` truoc.
- Neu ban do lich su khong tai, kiem tra `/api/historical-storms`; endpoint nay
  phai tra GeoJSON co san va khong tu tai NOAA trong request hien thi.
- Neu realtime khong co bao, demo Yagi mau va giai thich co che fallback.
