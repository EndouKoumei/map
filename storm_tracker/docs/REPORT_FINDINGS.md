# Ket Luan Phan Tich Du Lieu Bao

Tai lieu nay tom tat cac ket qua co the dua vao chuong ket qua thuc nghiem cua bao cao. So lieu lay tu `data/storms_vn.geojson` thong qua API `/api/dashboard-stats`.

## 1. Quy Mo Du Lieu

- Tong so bao/ap thap trong tap du lieu: 2,343.
- Giai doan: 1884-2026.
- So nam co du lieu: 143.
- Gio lon nhat ghi nhan: 170 kt.
- Nguon lich su: IBTrACS/NOAA.

## 2. Phan Cap Bao Theo Thang Viet Nam

| Phan cap | So luong |
| --- | ---: |
| Ap thap nhiet doi | 1,334 |
| Bao thuong | 216 |
| Bao manh | 170 |
| Bao rat manh | 340 |
| Sieu bao | 283 |

Nhan xet:

- Nhom ap thap nhiet doi chiem ty trong lon, phu hop voi viec tap du lieu gom ca cac he thong yeu.
- Cac cap bao rat manh va sieu bao van co so luong dang ke, can duoc nhan manh trong phan ung dung phong tranh thien tai.

## 3. Tinh Mua Vu

| Thang | So luong |
| --- | ---: |
| 7 | 424 |
| 8 | 441 |
| 9 | 487 |
| 10 | 355 |
| 11 | 296 |

Nhan xet:

- Mua bao tap trung ro tu thang 7 den thang 11.
- Thang 9 la dinh mua trong tap du lieu voi 487 truong hop.
- Cac thang dau nam co tan suat thap hon nhieu, dac biet thang 2 chi co 16 truong hop.

## 4. Xu Huong Theo Thap Ky

Mot so moc dang chu y:

| Thap ky | So luong | Gio TB kt | Sieu bao |
| --- | ---: | ---: | ---: |
| 1950s | 206 | 43.4 | 44 |
| 1960s | 237 | 46.6 | 41 |
| 1990s | 188 | 60.3 | 33 |
| 2000s | 161 | 64.0 | 33 |
| 2010s | 171 | 62.0 | 38 |
| 2020s | 98 | 67.3 | 22 |

Nhan xet:

- Du lieu gio truoc giai doan ve tinh co the thieu hoac kem dong nhat, vi vay khong nen ket luan truc tiep rang bao "tang do bien doi khi hau" chi tu bang nay.
- Tu sau 1950, thong tin gio day du hon va co the dung de so sanh tuong doi.
- Giai doan 2000-2026 co gio trung binh va ty le sieu bao cao hon giai doan 1884-1999 trong tap du lieu nay.

## 5. So Sanh Truoc/Sau Nam 2000

| Giai doan | So luong | Gio TB kt | So sieu bao | Ty le sieu bao |
| --- | ---: | ---: | ---: | ---: |
| 1884-1999 | 1,913 | 29.2 | 190 | 9.9% |
| 2000-2026 | 430 | 63.9 | 93 | 21.6% |

Nhan xet:

- Ty le sieu bao sau nam 2000 cao hon trong tap du lieu.
- Can trinh bay day la ket qua thong ke mo ta, chua phai bang chung nhan qua ve bien doi khi hau.
- Nguyen nhan co the den tu ca bien dong khi hau lan su cai thien cua quan trac ve tinh va chuan hoa du lieu.

## 6. Phan Bo Theo Vung Gan Viet Nam

| Vung | So luong |
| --- | ---: |
| Bac Bo | 761 |
| Trung Bo | 590 |
| Nam Bo | 164 |
| Ngoai vung ven bien VN | 828 |

Nhan xet:

- Bac Bo va Trung Bo co so luong track lien quan cao hon Nam Bo trong cach phan vung hien tai.
- Ket qua nay la xap xi theo toa do track, chua phai thong ke do bo theo tinh.
- Neu muon ket luan theo tinh ven bien, can bo sung polygon dia gioi tinh va thuat toan xac dinh landfall.

## 7. Top Bao Manh Nhat

| Hang | Ten bao | Nam | Gio max |
| --- | --- | ---: | ---: |
| 1 | JOAN | 1959 | 170 kt |
| 2 | OPAL | 1964 | 170 kt |
| 3 | MERANTI | 2016 | 170 kt |
| 4 | GONI | 2020 | 170 kt |
| 5 | HAIYAN | 2013 | 165 kt |

## 8. Ket Luan Co The Dua Vao Bao Cao

He thong da truc quan hoa va phan tich duoc tap du lieu bao lon trong 143 nam, gom 2,343 he thong nhiet doi anh huong den khu vuc Tay Bac Thai Binh Duong va vung bien Viet Nam. Ket qua cho thay tinh mua vu ro ret, voi tan suat cao nhat trong giai doan thang 7-10 va dinh mua vao thang 9. Phan tich theo cap do cho thay ben canh nhom ap thap nhiet doi, so luong bao rat manh va sieu bao van dang ke, khang dinh nhu cau co cong cu tra cuu lich su va so sanh cac kich ban bao tuong tu.

Khi so sanh truoc va sau nam 2000, tap du lieu ghi nhan ty le sieu bao cao hon trong giai doan gan day. Tuy nhien, ket qua nay nen duoc dien giai than trong vi chat luong quan trac va muc do day du cua du lieu thay doi theo thoi gian. Do do, dong gop chinh cua do an la xay dung he thong WebGIS co kha nang khai thac, truc quan hoa, so sanh va ho tro phan tich du lieu bao, hon la dua ra ket luan nhan qua ve khi hau.

## 9. Gioi Han Va Huong Phat Trien

- Phan vung Bac/Trung/Nam hien la xap xi theo toa do, chua co tinh toan do bo theo tinh.
- M2 phu thuoc nguon du lieu ngoai; fallback Yagi 2024 giup demo on dinh nhung khong thay the du lieu realtime khi co bao that.
- Heatmap the hien mat do diem/track theo khong gian, khong phai xac suat thiet hai.
- Huong phat trien: bo sung dia gioi tinh ven bien, tinh landfall, canh bao vung anh huong Viet Nam va cone du bao bat dinh.
