#!/usr/bin/env python3

import pandas as pd
import json
import requests
from collections import defaultdict
from datetime import datetime
import os
import sys
from pathlib import Path

# Cấu hình
IBTRACS_URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv"
CACHE_DIR = "data_cache"
OUTPUT_DIR = "output"

# Vùng biển Việt Nam
LAT_MIN, LAT_MAX = 5.0, 25.0
LON_MIN, LON_MAX = 100.0, 120.0

class StormDataProcessor:
    def __init__(self, cache_dir=CACHE_DIR, output_dir=OUTPUT_DIR):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message):
        """In log với timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def download_data(self, force=False):
        """Tải dữ liệu từ NOAA"""
        cache_file = self.cache_dir / "ibtracs.WP.list.v04r01.csv"
        
        # Kiểm tra cache
        if cache_file.exists() and not force:
            file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            days_old = file_age / (24 * 3600)
            
            if days_old < 7:  # Cache còn mới (dưới 1 tuần)
                self.log(f"Sử dụng cache (cập nhật {days_old:.1f} ngày trước)")
                return cache_file
        
        # Tải dữ liệu mới
        self.log(f"Đang tải dữ liệu từ NOAA...")
        try:
            response = requests.get(IBTRACS_URL, stream=True, timeout=60)
            response.raise_for_status()
            
            # Lưu file
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(cache_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            print(f"\rTiến trình: {progress:.1f}%", end='')
            
            print()  # Newline sau progress bar
            self.log(f"Đã tải xong {downloaded / (1024*1024):.1f} MB")
            return cache_file
            
        except requests.RequestException as e:
            self.log(f"LỖI khi tải dữ liệu: {e}")
            if cache_file.exists():
                self.log("Sử dụng cache cũ")
                return cache_file
            raise

    def classify_vietnam_category(self, wind_speed_kt):
        """
        Phân loại cấp bão theo tiêu chuẩn Việt Nam
        """
        if wind_speed_kt is None or pd.isna(wind_speed_kt):
            return "Không có dữ liệu"
        
        try:
            wind_speed_kt = float(wind_speed_kt)
        except (ValueError, TypeError):
            return "Không có dữ liệu"
            
        wind_kmh = wind_speed_kt * 1.852
        
        if wind_kmh < 39: 
            return "Vùng áp thấp"
        elif 39 <= wind_kmh < 62: 
            return "Áp thấp nhiệt đới"
        elif 62 <= wind_kmh < 89: 
            return "Bão thường"
        elif 89 <= wind_kmh < 118: 
            return "Bão mạnh"
        elif 118 <= wind_kmh < 184: 
            return "Bão rất mạnh"
        else:  # >= 184
            return "Siêu bão"
    
    def get_max_category(self, categories):
        """Lấy cấp bão cao nhất từ danh sách categories"""
        category_order = {
            "Không có dữ liệu": 0,
            "Vùng áp thấp": 1,
            "Áp thấp nhiệt đới": 2,
            "Bão thường": 3,
            "Bão mạnh": 4,
            "Bão rất mạnh": 5,
            "Siêu bão": 6
        }
        
        max_level = 0
        max_cat = "Không có dữ liệu"
        
        for cat in categories:
            if cat in category_order and category_order[cat] > max_level:
                max_level = category_order[cat]
                max_cat = cat
        
        return max_cat
    
    def process_data(self, csv_file):
        """Xử lý dữ liệu CSV"""
        self.log("Đang đọc file CSV...")
        
        # Đọc file với skiprows để bỏ header thứ 2
        df = pd.read_csv(csv_file, skiprows=[1], low_memory=False)
        
        self.log(f"Đã đọc {len(df):,} dòng dữ liệu")
        
        # Chọn các cột cần thiết
        required_cols = ['SID', 'SEASON', 'NAME', 'ISO_TIME', 'LAT', 'LON', 'USA_WIND', 'USA_PRES']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols].copy()
        
        # Chuyển đổi kiểu dữ liệu
        df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
        df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
        
        # Lọc theo vùng biển Việt Nam
        self.log("Đang lọc dữ liệu theo vùng biển Việt Nam...")
        vn_df = df[
            (df['LAT'] >= LAT_MIN) & (df['LAT'] <= LAT_MAX) &
            (df['LON'] >= LON_MIN) & (df['LON'] <= LON_MAX)
        ].copy()
        
        # Xóa các dòng thiếu tọa độ
        vn_df = vn_df.dropna(subset=['LAT', 'LON'])
        
        # Phân loại cấp bão
        self.log("Đang phân loại bão...")
        vn_df['vn_category'] = vn_df['USA_WIND'].apply(self.classify_vietnam_category)

        # Sắp xếp theo định danh bão và thời gian
        vn_df = vn_df.sort_values(by=['SID', 'ISO_TIME'])
        
        self.log(f"Tìm thấy {len(vn_df):,} điểm dữ liệu trong vùng biển VN")
        
        # Thống kê số cơn bão
        num_storms = vn_df['SID'].nunique()
        self.log(f"Số cơn bão/áp thấp: {num_storms}")
        
        # ✅ In thống kê phân loại
        category_counts = vn_df.groupby('vn_category').size().sort_values(ascending=False)
        self.log("\n📊 Phân bổ cấp bão:")
        for cat, count in category_counts.items():
            self.log(f"  • {cat}: {count:,} điểm ({count/len(vn_df)*100:.1f}%)")
        
        return vn_df
    
    def create_geojson(self, df):
        """Tạo GeoJSON từ DataFrame"""
        self.log("Đang tạo GeoJSON...")
        
        # Nhóm theo SID (Storm ID)
        groups = df.groupby('SID')
        
        features = []
        
        for sid, group in groups:
            # Tạo danh sách tọa độ [lon, lat]
            coords = list(zip(group['LON'].tolist(), group['LAT'].tolist()))
            
            # Lấy thông tin cơn bão
            name = group['NAME'].iloc[0] if 'NAME' in group.columns else 'UNKNOWN'
            season = group['SEASON'].iloc[0] if 'SEASON' in group.columns else 'N/A'
            
            # ✅ Lấy cấp bão cao nhất (dùng tên mới)
            if 'vn_category' in group.columns:
                vn_categories = group['vn_category'].dropna().tolist()
                vn_category = self.get_max_category(vn_categories) if vn_categories else "Không có dữ liệu"
            else:
                vn_category = "Không có dữ liệu"
            
            # Tính toán cường độ trung bình và max
            if 'USA_WIND' in group.columns:
                wind_data = pd.to_numeric(group['USA_WIND'], errors='coerce')
                max_wind = wind_data.max()
                avg_wind = wind_data.mean()
                max_wind_kmh = max_wind * 1.852 if pd.notna(max_wind) else None
                avg_wind_kmh = avg_wind * 1.852 if pd.notna(avg_wind) else None
            else:
                max_wind = avg_wind = max_wind_kmh = avg_wind_kmh = None
            
            if 'USA_PRES' in group.columns:
                pres_data = pd.to_numeric(group['USA_PRES'], errors='coerce')
                min_pres = pres_data.min()
            else:
                min_pres = None
            
            # Tạo feature
            feature = {
                "type": "Feature",
                "properties": {
                    "sid": sid,
                    "name": str(name),
                    "season": str(season),
                    "vn_category": vn_category,  # ✅ Tên mới
                    "max_wind_kt": float(max_wind) if pd.notna(max_wind) else None,
                    "max_wind_kmh": float(max_wind_kmh) if max_wind_kmh is not None else None,
                    "avg_wind_kt": float(avg_wind) if pd.notna(avg_wind) else None,
                    "avg_wind_kmh": float(avg_wind_kmh) if avg_wind_kmh is not None else None,
                    "min_pressure_mb": float(min_pres) if pd.notna(min_pres) else None,
                    "points": len(coords),
                    "start_time": str(group['ISO_TIME'].iloc[0]) if 'ISO_TIME' in group.columns else None,
                    "end_time": str(group['ISO_TIME'].iloc[-1]) if 'ISO_TIME' in group.columns else None
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }
            
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated": datetime.now().isoformat(),
                "source": "NOAA IBTrACS v04r01",
                "region": "Vietnam Waters",
                "bounds": {
                    "lat": [LAT_MIN, LAT_MAX],
                    "lon": [LON_MIN, LON_MAX]
                },
                "total_storms": len(features)
            }
        }
        
        self.log(f"Đã tạo GeoJSON với {len(features)} cơn bão")
        
        return geojson
    
    def save_geojson(self, geojson, filename="vietnam_storms.geojson"):
        """Lưu GeoJSON ra file"""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        self.log(f"Đã lưu: {output_file}")
        return output_file
    
    def run(self, force_download=False):
        """Chạy toàn bộ quy trình"""
        self.log("=== BẮT ĐẦU XỬ LÝ DỮ LIỆU BÃO ===")
        
        try:
            # 1. Tải dữ liệu
            csv_file = self.download_data(force=force_download)
            
            # 2. Xử lý dữ liệu
            df = self.process_data(csv_file)
            
            # 3. Tạo GeoJSON
            geojson = self.create_geojson(df)
            
            # 4. Lưu GeoJSON
            self.save_geojson(geojson)
            
            self.log("=== HOÀN THÀNH ===")
            return True
            
        except Exception as e:
            self.log(f"LỖI: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Hàm main"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Tải và xử lý dữ liệu bão từ NOAA IBTrACS'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Bắt buộc tải lại dữ liệu dù đã có cache'
    )
    parser.add_argument(
        '--cache-dir',
        default=CACHE_DIR,
        help=f'Thư mục cache (mặc định: {CACHE_DIR})'
    )
    parser.add_argument(
        '--output-dir',
        default=OUTPUT_DIR,
        help=f'Thư mục output (mặc định: {OUTPUT_DIR})'
    )
    
    args = parser.parse_args()
    
    processor = StormDataProcessor(
        cache_dir=args.cache_dir,
        output_dir=args.output_dir
    )
    
    success = processor.run(force_download=args.force)
    sys.exit(0 if success is not False else 1)


if __name__ == "__main__":
    main()