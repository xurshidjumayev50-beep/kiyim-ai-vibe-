import os
import uuid
import json
import base64
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from services.db import (
    init_db, get_profile, update_profile,
    get_garments, add_garment,
    add_tryon_session, get_tryon_sessions,
    delete_tryon_session, clear_all_tryon_sessions
)
from services.fit_engine import fit_engine
from services.tryon_engine import tryon_engine

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
GARMENT_FOLDER = os.path.join(BASE_DIR, "static", "garments")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GARMENT_FOLDER, exist_ok=True)

# Ma'lumotlar bazasini ishga tushirish
init_db()

@app.route("/")
def index():
    """Mobil Ilovaning Asosiy Interfeysi (PWA / Mobile App UI)"""
    profile = get_profile()
    garments = get_garments()
    return render_template("index.html", profile=profile, garments=garments)

@app.route("/api/profile", methods=["GET", "POST"])
def profile_endpoint():
    if request.method == "POST":
        data = request.json or {}
        p = update_profile(
            full_name=data.get("full_name", "Foydalanuvchi"),
            height_cm=float(data.get("height_cm", 175.0)),
            weight_kg=float(data.get("weight_kg", 70.0)),
            gender=data.get("gender", "male"),
            preferred_size=data.get("preferred_size", "M")
        )
        return jsonify({"success": True, "profile": p})
    return jsonify(get_profile())

@app.route("/api/garments", methods=["GET", "POST"])
def garments_endpoint():
    if request.method == "POST":
        title = request.form.get("title", "Yangi Kiyim")
        category = request.form.get("category", "upper_body")
        sizes_raw = request.form.get("sizes", '["S", "M", "L", "XL"]')
        try:
            sizes = json.loads(sizes_raw)
        except:
            sizes = ["S", "M", "L", "XL"]

        file = request.files.get("image")
        if not file:
            return jsonify({"error": "Kiyim rasmi talab qilinadi"}), 400

        filename = f"garment_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(GARMENT_FOLDER, filename)
        file.save(filepath)

        img_url = f"/static/garments/{filename}"
        gid = add_garment(title, category, img_url, sizes)
        return jsonify({"success": True, "id": gid, "image_url": img_url})

    return jsonify(get_garments())

@app.route("/api/tryon", methods=["POST"])
def tryon_endpoint():
    """
    Virtual Try-On va Fit Detection so'rovi:
    Foydalanuvchi rasmi va Kiyim rasmi qabul qilinadi.
    """
    try:
        user_image_path = None
        user_image_rel = None

        # 1. Foydalanuvchi rasmini qabul qilish (File yoki Base64 / URL)
        if "user_image" in request.files:
            file = request.files["user_image"]
            filename = f"user_{uuid.uuid4().hex[:8]}.jpg"
            user_image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(user_image_path)
            user_image_rel = f"/static/uploads/{filename}"
        elif request.is_json and request.json.get("user_image_base64"):
            b64_str = request.json["user_image_base64"].split(",")[-1]
            filename = f"user_{uuid.uuid4().hex[:8]}.jpg"
            user_image_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(user_image_path, "wb") as f:
                f.write(base64.b64decode(b64_str))
            user_image_rel = f"/static/uploads/{filename}"
        elif request.form.get("user_image_url"):
            user_image_rel = request.form.get("user_image_url")
            user_image_path = os.path.join(BASE_DIR, user_image_rel.lstrip("/"))
        else:
            # Standart sinov rasmidan foydalanish
            sample = os.path.join(UPLOAD_FOLDER, "sample_user.jpg")
            if os.path.exists(sample):
                user_image_path = sample
                user_image_rel = "/static/uploads/sample_user.jpg"
            else:
                return jsonify({"error": "Foydalanuvchi rasmi yuklanmadi"}), 400

        # 2. Kiyim rasmini aniqlash
        garment_image_path = None
        garment_image_rel = None

        if "garment_image" in request.files:
            file = request.files["garment_image"]
            filename = f"garment_{uuid.uuid4().hex[:8]}.jpg"
            garment_image_path = os.path.join(GARMENT_FOLDER, filename)
            file.save(garment_image_path)
            garment_image_rel = f"/static/garments/{filename}"
        elif request.form.get("garment_url") or (request.is_json and request.json.get("garment_url")):
            garment_image_rel = (request.form.get("garment_url") or request.json.get("garment_url"))
            garment_image_path = os.path.join(BASE_DIR, garment_image_rel.lstrip("/"))
        else:
            # Standart birinchi kiyim
            default_g = os.path.join(GARMENT_FOLDER, "garment_1.jpg")
            garment_image_path = default_g
            garment_image_rel = "/static/garments/garment_1.jpg"

        selected_size = (
            request.form.get("selected_size") or 
            (request.json.get("selected_size") if request.is_json else None) or 
            "M"
        )

        # 3. O'lcham va Moslik (Size & Fit) Tahlili
        fit_results = fit_engine.analyze_person(user_image_path, selected_size)

        # 4. Virtual Try-On Overlay Ishlab Chiqish (Anatomik moslashish & o'lcham effekti)
        res_filename = f"tryon_{uuid.uuid4().hex[:10]}.jpg"
        res_filepath = os.path.join(UPLOAD_FOLDER, res_filename)
        tryon_engine.overlay_garment(
            user_image_path,
            garment_image_path,
            res_filepath,
            fit_mode=fit_results["fit_status"]
        )
        result_image_rel = f"/static/uploads/{res_filename}"

        # 5. Tarixga saqlash
        session_id = add_tryon_session(
            user_image_url=user_image_rel,
            garment_image_url=garment_image_rel,
            result_image_url=result_image_rel,
            fit_status=fit_results["fit_status"],
            match_percentage=fit_results["match_percentage"],
            recommended_size=fit_results["recommended_size"],
            fit_advice=fit_results["fit_advice"],
            body_metrics=fit_results["body_metrics"]
        )

        return jsonify({
            "success": True,
            "session_id": session_id,
            "result_image_url": result_image_rel,
            "user_image_url": user_image_rel,
            "garment_image_url": garment_image_rel,
            "fit_status": fit_results["fit_status"],
            "match_percentage": fit_results["match_percentage"],
            "recommended_size": fit_results["recommended_size"],
            "fit_advice": fit_results["fit_advice"],
            "body_metrics": fit_results["body_metrics"]
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def history_endpoint():
    return jsonify(get_tryon_sessions())

@app.route("/api/history/<int:session_id>", methods=["DELETE"])
def delete_history_endpoint(session_id):
    ok = delete_tryon_session(session_id)
    return jsonify({"success": ok})

@app.route("/api/history", methods=["DELETE"])
def clear_history_endpoint():
    ok = clear_all_tryon_sessions()
    return jsonify({"success": ok})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("=" * 60)
    print("👗 Kiyim AI Mobil Ilova & Serveri Ishga Tushmoqda...")
    print(f"📱 Brauzer yoki telefoningizdan oching: http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
