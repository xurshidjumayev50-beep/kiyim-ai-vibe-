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
from services.body_measure import body_measurer
from services.size_chart import fit_check, SIZE_CHART

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

        g_bytes = file.read()
        img_url = f"data:image/jpeg;base64,{base64.b64encode(g_bytes).decode('utf-8')}"
        gid = add_garment(title, category, img_url, sizes)
        return jsonify({"success": True, "id": gid, "image_url": img_url})

    return jsonify(get_garments())

@app.route("/api/measure", methods=["POST"])
def measure_endpoint():
    """
    Tana o'lchamlari (santimetrda) va moslik tahlili (Fit Detection).
    Rasm serverda saqlanmaydi (faqat xotirada MediaPipe orqali tahlil qilinadi).
    """
    try:
        gender = request.form.get("gender") or (request.json.get("gender") if request.is_json else None) or "male"
        height_str = request.form.get("height") or request.form.get("height_cm") or (request.json.get("height") if request.is_json else None) or (request.json.get("height_cm") if request.is_json else None)
        weight_str = request.form.get("weight") or request.form.get("weight_kg") or (request.json.get("weight") if request.is_json else None) or (request.json.get("weight_kg") if request.is_json else None)
        selected_size = request.form.get("size") or request.form.get("selected_size") or (request.json.get("size") if request.is_json else None) or (request.json.get("selected_size") if request.is_json else None) or "M"

        # Agar oldindan tana o'lchamlari ma'lum bo'lsa (o'lcham tugmasini o'zgartirganda tezkor qayta hisoblash)
        cached_body = request.json.get("body") if request.is_json else None
        cached_landmarks = request.json.get("landmarks") if request.is_json else None

        if cached_body:
            fit_res = fit_check(cached_body, selected_size, landmarks=cached_landmarks)
            return jsonify({
                "success": True,
                "body": cached_body,
                "landmarks": cached_landmarks or [],
                "fit": fit_res
            })

        if not height_str or not weight_str:
            return jsonify({"success": False, "error": "Bo'y va vazn maydonlari to'ldirilishi shart"}), 400

        try:
            height_cm = float(height_str)
            weight_kg = float(weight_str)
        except ValueError:
            return jsonify({"success": False, "error": "Bo'y va vazn raqamda kiritilishi kerak"}), 400

        # Rasm ma'lumotini olish (Fayl yoki Base64) - diskka saqlanmaydi
        image_bytes = None
        if "image" in request.files:
            image_bytes = request.files["image"].read()
        elif "user_image" in request.files:
            image_bytes = request.files["user_image"].read()
        elif request.is_json and request.json.get("image_base64"):
            b64_str = request.json["image_base64"].split(",")[-1]
            image_bytes = base64.b64decode(b64_str)
        elif request.form.get("image_base64"):
            b64_str = request.form.get("image_base64").split(",")[-1]
            image_bytes = base64.b64decode(b64_str)

        if not image_bytes:
            return jsonify({"success": False, "error": "Foydalanuvchi rasmi yuklanmadi"}), 400

        # MediaPipe Pose orqali tana o'lchovlarini santimetrda aniqlash
        body_metrics = body_measurer.measure(
            image_data=image_bytes,
            height_cm=height_cm,
            weight_kg=weight_kg,
            gender=gender
        )

        # Tanlangan o'lcham bo'yicha moslik tahlili (fit_check)
        fit_results = fit_check(
            body=body_metrics,
            size=selected_size,
            landmarks=body_metrics.get("landmarks")
        )

        return jsonify({
            "success": True,
            "body": {
                "shoulder_cm": body_metrics["shoulder_cm"],
                "chest_cm": body_metrics["chest_cm"],
                "waist_cm": body_metrics["waist_cm"],
                "hip_cm": body_metrics["hip_cm"],
                "confidence": body_metrics["confidence"]
            },
            "landmarks": body_metrics.get("landmarks", []),
            "fit": fit_results
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Tahlil jarayonida xatolik: {str(e)}"}), 500

@app.route("/api/tryon", methods=["POST"])
def tryon_endpoint():
    """
    Virtual Try-On va Fit Detection so'rovi:
    Barcha jarayon xotirada bajariladi, server diskida rasm saqlanmaydi.
    """
    try:
        user_bytes = None
        user_data_url = None

        # 1. Foydalanuvchi rasmini qabul qilish (File yoki Base64 / URL)
        if "user_image" in request.files:
            user_bytes = request.files["user_image"].read()
        elif request.is_json and request.json.get("user_image_base64"):
            b64_str = request.json["user_image_base64"].split(",")[-1]
            user_bytes = base64.b64decode(b64_str)
        elif request.form.get("user_image_base64"):
            b64_str = request.form.get("user_image_base64").split(",")[-1]
            user_bytes = base64.b64decode(b64_str)
        elif request.form.get("user_image_url"):
            rel = request.form.get("user_image_url")
            if rel.startswith("data:"):
                b64_str = rel.split(",")[-1]
                user_bytes = base64.b64decode(b64_str)
            else:
                p = os.path.join(BASE_DIR, rel.lstrip("/"))
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        user_bytes = f.read()

        if not user_bytes:
            return jsonify({"success": False, "error": "Foydalanuvchi rasmi yuklanmadi"}), 400

        user_data_url = f"data:image/jpeg;base64,{base64.b64encode(user_bytes).decode('utf-8')}"

        # 2. Kiyim rasmini aniqlash
        garment_bytes = None
        garment_url_str = None
        if "garment_image" in request.files:
            garment_bytes = request.files["garment_image"].read()
            garment_url_str = f"data:image/jpeg;base64,{base64.b64encode(garment_bytes).decode('utf-8')}"
        elif request.form.get("garment_url") or (request.is_json and request.json.get("garment_url")):
            g_url = request.form.get("garment_url") or request.json.get("garment_url")
            garment_url_str = g_url
            if g_url.startswith("data:"):
                b64_str = g_url.split(",")[-1]
                garment_bytes = base64.b64decode(b64_str)
            else:
                p = os.path.join(BASE_DIR, g_url.lstrip("/"))
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        garment_bytes = f.read()
        elif request.is_json and request.json.get("garment_image_base64"):
            b64_str = request.json["garment_image_base64"].split(",")[-1]
            garment_bytes = base64.b64decode(b64_str)
            garment_url_str = f"data:image/jpeg;base64,{b64_str}"

        if not garment_bytes:
            return jsonify({"success": False, "error": "Kiyim rasmi yuklanmadi"}), 400

        selected_size = (
            request.form.get("selected_size") or 
            request.form.get("size") or
            (request.json.get("selected_size") if request.is_json else None) or 
            (request.json.get("size") if request.is_json else None) or 
            "M"
        )

        gender = request.form.get("gender") or (request.json.get("gender") if request.is_json else None) or "male"
        height_str = request.form.get("height") or request.form.get("height_cm") or (request.json.get("height") if request.is_json else None) or "175"
        weight_str = request.form.get("weight") or request.form.get("weight_kg") or (request.json.get("weight") if request.is_json else None) or "70"

        try:
            height_cm = float(height_str)
            weight_kg = float(weight_str)
        except ValueError:
            height_cm, weight_kg = 175.0, 70.0

        # 3. O'lcham va Moslik (Size & Fit) Tahlili
        fit_status = "ok"
        match_percentage = 88
        recommended_size = selected_size
        fit_advice = "Kiyim sizga mos keladi."
        body_metrics = {}

        try:
            body_metrics = body_measurer.measure(
                image_data=user_bytes,
                height_cm=height_cm,
                weight_kg=weight_kg,
                gender=gender
            )
            fit_res = fit_check(
                body=body_metrics,
                size=selected_size,
                landmarks=body_metrics.get("landmarks")
            )
            fit_status = fit_res.get("fit_mode", "ok")
            match_percentage = int(fit_res.get("fit_score", 88))
            recommended_size = fit_res.get("recommended_size", selected_size)
            fit_advice = fit_res.get("summary", "O'lcham tahlili yakunlandi.")
        except Exception as e:
            # Pose aniqlanmagan taqdirda xatolik bermay umumiy o'lcham bo'yicha hisoblash
            pass

        # 4. Virtual Try-On Overlay Ishlab Chiqish (Faqat xotirada)
        res_bytes = tryon_engine.overlay_garment_in_memory(
            user_bytes,
            garment_bytes,
            size=selected_size,
            fit_mode=fit_status
        )
        res_b64 = f"data:image/jpeg;base64,{base64.b64encode(res_bytes).decode('utf-8')}"

        # 5. Tarixga saqlash
        session_id = add_tryon_session(
            user_image_url=user_data_url,
            garment_image_url=garment_url_str or "",
            result_image_url=res_b64,
            fit_status=fit_status,
            match_percentage=match_percentage,
            recommended_size=recommended_size,
            fit_advice=fit_advice,
            body_metrics=body_metrics
        )

        return jsonify({
            "success": True,
            "session_id": session_id,
            "result_image_url": res_b64,
            "user_image_url": user_data_url,
            "garment_image_url": garment_url_str,
            "fit_status": fit_status,
            "match_percentage": match_percentage,
            "recommended_size": recommended_size,
            "fit_advice": fit_advice,
            "body_metrics": body_metrics
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
