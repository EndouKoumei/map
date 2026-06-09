"""
Storm Tracker – Hệ thống theo dõi và phân tích bão Việt Nam
Tích hợp M1 (Lịch sử) + M2 (Thời gian thực)
ĐATN 2025.2 – Đặng Hồng Minh – 20225740
"""
from flask import Flask, jsonify, render_template, send_file, request
from flask_cors import CORS
import os, time
from data.fetcher import StormRealtimeFetcher
from data.similarity import find_similar

app = Flask(__name__)
CORS(app)

fetcher = StormRealtimeFetcher()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_PATH = os.path.join(BASE_DIR, 'data', 'storms_vn.geojson')
# ══════════════════════════════════════════════════════════════════
# TRANG WEB
# ══════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    """Trang chủ → redirect về M1 (Lịch sử)"""
    return render_template('m1_map.html')

@app.route('/historical')
def historical():
    """M1 – Bản đồ lịch sử bão"""
    return render_template('m1_map.html')

@app.route('/realtime')
def realtime():
    """M2 – Theo dõi bão thời gian thực"""
    return render_template('index.html')

# ══════════════════════════════════════════════════════════════════
# API – DỮ LIỆU LỊCH SỬ (M1)
# ══════════════════════════════════════════════════════════════════

@app.route('/api/historical-storms')
def historical_storms():
    """
    Trả về toàn bộ GeoJSON lịch sử bão (~14MB).
    Dùng send_file để stream trực tiếp, không load vào RAM.
    """
    if not os.path.exists(HISTORICAL_PATH):
        return jsonify({
            "error": "Chưa có dữ liệu lịch sử.",
            "fix":   "Chạy lệnh: python m1_process_data.py"
        }), 404
    return send_file(
        HISTORICAL_PATH,
        mimetype='application/json',
        as_attachment=False
    )

# ══════════════════════════════════════════════════════════════════
# API – BÃO THỜI GIAN THỰC (M2)
# ══════════════════════════════════════════════════════════════════

@app.route('/api/active-storms')
def active_storms():
    try:
        force_refresh = request.args.get("refresh") == "1"
        return jsonify(fetcher.get_active_storms(force_refresh=force_refresh))
    except Exception as e:
        return jsonify({
            "type": "FeatureCollection",
            "error": str(e),
            "features": [],
        }), 500

@app.route('/api/forecast/<storm_id>')
def storm_forecast(storm_id):
    try:
        return jsonify(fetcher.get_forecast(storm_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/storm/<storm_id>')
def storm_detail(storm_id):
    try:
        return jsonify(fetcher.get_storm_detail(storm_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════════════════════════
# API – SO SÁNH BÃO LỊCH SỬ TƯƠNG TỰ (M3)
# ══════════════════════════════════════════════════════════════════

@app.route('/api/similar-storms/<storm_id>')
def similar_storms(storm_id):
    """M3: Tìm top-5 bão lịch sử tương tự nhất bằng DTW."""
    try:
        top_k = int(request.args.get('k', 5))
        return jsonify(find_similar(storm_id, top_k=top_k))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════════════════════════
# API – TRẠNG THÁI HỆ THỐNG
# ══════════════════════════════════════════════════════════════════

@app.route('/api/status')
def status():
    historical_ok = os.path.exists(HISTORICAL_PATH)
    historical_size = (
        round(os.path.getsize(HISTORICAL_PATH) / 1024 / 1024, 1)
        if historical_ok else 0
    )
    return jsonify({
        "system":            "Storm Tracker VN",
        "version":           "2.1 (M1+M2+M3)",
        "modules": {
            "M1_historical": {
                "status":     "ready" if historical_ok else "no_data",
                "file_size_mb": historical_size,
                "endpoint":   "/api/historical-storms"
            },
            "M2_realtime": {
                "status":       "ready",
                "last_update":  fetcher.last_update,
                "storm_count":  fetcher.storm_count,
                "source":       "JTWC via tropycal",
                "endpoint":     "/api/active-storms"
            },
            "M3_similarity": {
                "status":       "ready" if historical_ok else "no_data",
                "method":       "DTW + cosine multi-factor score",
                "endpoint":     "/api/similar-storms/<storm_id>"
            }
        }
    })

# ══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🌀 Storm Tracker VN – v2.1 (M1 + M2 + M3)")
    print("="*50)
    print("  📚 Lịch sử:  http://localhost:5000/")
    print("  📡 Thực tế:  http://localhost:5000/realtime")
    print("  🔧 Trạng thái: http://localhost:5000/api/status")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
