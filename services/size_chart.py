import numpy as np

# Kiyim o'lchamlari jadvali (santimetrda) — oson tahrirlanadigan namuna
SIZE_CHART = {
    "XS": {
        "shoulder_width": 43.0,
        "chest_width": 46.0,   # Aylana: 92.0 sm
        "waist_width": 41.0,   # Aylana: 82.0 sm
        "hip_width": 46.0,     # Aylana: 92.0 sm
        "length": 65.0
    },
    "S": {
        "shoulder_width": 45.0,
        "chest_width": 49.0,   # Aylana: 98.0 sm
        "waist_width": 44.0,   # Aylana: 88.0 sm
        "hip_width": 49.0,     # Aylana: 98.0 sm
        "length": 68.0
    },
    "M": {
        "shoulder_width": 47.0,
        "chest_width": 53.0,   # Aylana: 106.0 sm
        "waist_width": 47.5,   # Aylana: 95.0 sm
        "hip_width": 53.0,     # Aylana: 106.0 sm
        "length": 71.0
    },
    "L": {
        "shoulder_width": 49.5,
        "chest_width": 57.0,   # Aylana: 114.0 sm
        "waist_width": 51.5,   # Aylana: 103.0 sm
        "hip_width": 57.0,     # Aylana: 114.0 sm
        "length": 74.0
    },
    "XL": {
        "shoulder_width": 52.0,
        "chest_width": 61.0,   # Aylana: 122.0 sm
        "waist_width": 55.5,   # Aylana: 111.0 sm
        "hip_width": 61.0,     # Aylana: 122.0 sm
        "length": 77.0
    },
    "XXL": {
        "shoulder_width": 54.5,
        "chest_width": 65.5,   # Aylana: 131.0 sm
        "waist_width": 60.0,   # Aylana: 120.0 sm
        "hip_width": 65.5,     # Aylana: 131.0 sm
        "length": 80.0
    }
}

ORDERED_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

def compute_zone_boxes(landmarks: list) -> dict:
    """
    MediaPipe landmarks koordinatalari asosida 4 ta zonaning (yelka, ko'krak, bel, bo'ksa)
    normallashtirilgan chegaraviy qutilarini (box) hisoblaydi.
    """
    if not landmarks or len(landmarks) < 25:
        # Fallback standart nisbatlar
        return {
            "shoulder": {"x": 0.28, "y": 0.20, "width": 0.44, "height": 0.08},
            "chest":    {"x": 0.30, "y": 0.27, "width": 0.40, "height": 0.12},
            "waist":    {"x": 0.32, "y": 0.38, "width": 0.36, "height": 0.10},
            "hip":      {"x": 0.30, "y": 0.47, "width": 0.40, "height": 0.12}
        }

    ls = landmarks[11]  # chap yelka
    rs = landmarks[12]  # o'ng yelka
    lh = landmarks[23]  # chap son
    rh = landmarks[24]  # o'ng son

    ls_x, ls_y = float(ls["x"]), float(ls["y"])
    rs_x, rs_y = float(rs["x"]), float(rs["y"])
    lh_x, lh_y = float(lh["x"]), float(lh["y"])
    rh_x, rh_y = float(rh["x"]), float(rh["y"])

    shoulder_mid_x = (ls_x + rs_x) / 2.0
    shoulder_mid_y = (ls_y + rs_y) / 2.0
    hip_mid_x = (lh_x + rh_x) / 2.0
    hip_mid_y = (lh_y + rh_y) / 2.0

    torso_h = max(0.12, hip_mid_y - shoulder_mid_y)
    shoulder_w = max(0.18, abs(ls_x - rs_x))
    hip_w = max(0.14, abs(lh_x - rh_x))

    # 1. Yelka (yelka nuqtalari)
    sh_box_x = max(0.01, min(ls_x, rs_x) - 0.04)
    sh_box_y = max(0.01, shoulder_mid_y - 0.04)
    sh_box_w = min(0.98 - sh_box_x, shoulder_w + 0.08)
    sh_box_h = min(0.14, torso_h * 0.25)

    # 2. Ko'krak (yelka va qovurg'a oralig'i)
    ch_box_x = max(0.01, min(ls_x, rs_x) - 0.02)
    ch_box_y = shoulder_mid_y + torso_h * 0.15
    ch_box_w = min(0.98 - ch_box_x, shoulder_w + 0.04)
    ch_box_h = torso_h * 0.32

    # 3. Bel (kindik atrofi)
    waist_w = (shoulder_w * 0.85 + hip_w) / 2.0
    w_box_x = max(0.01, (shoulder_mid_x + hip_mid_x) / 2.0 - waist_w / 2.0)
    w_box_y = shoulder_mid_y + torso_h * 0.48
    w_box_w = min(0.98 - w_box_x, waist_w)
    w_box_h = torso_h * 0.28

    # 4. Bo'ksa (son / tos qismi)
    hip_box_w = hip_w + 0.08
    h_box_x = max(0.01, min(lh_x, rh_x) - 0.04)
    h_box_y = shoulder_mid_y + torso_h * 0.75
    h_box_w = min(0.98 - h_box_x, hip_box_w)
    h_box_h = torso_h * 0.32

    return {
        "shoulder": {
            "x": round(sh_box_x, 4),
            "y": round(sh_box_y, 4),
            "width": round(sh_box_w, 4),
            "height": round(sh_box_h, 4)
        },
        "chest": {
            "x": round(ch_box_x, 4),
            "y": round(ch_box_y, 4),
            "width": round(ch_box_w, 4),
            "height": round(ch_box_h, 4)
        },
        "waist": {
            "x": round(w_box_x, 4),
            "y": round(w_box_y, 4),
            "width": round(w_box_w, 4),
            "height": round(w_box_h, 4)
        },
        "hip": {
            "x": round(h_box_x, 4),
            "y": round(h_box_y, 4),
            "width": round(h_box_w, 4),
            "height": round(h_box_h, 4)
        }
    }

def fit_check(body: dict, size: str = "M", landmarks: list = None) -> dict:
    """
    Tana o'lchamlari va tanlangan kiyim o'lchami bo'yicha moslikni (ease) tekshiradi.
    Har zona uchun (yelka, ko'krak, bel, bo'ksa):
      ease = kiyim aylanasi (kenglik x 2) - tana aylanasi.
      ease < 4: "tight" (Tor)
      4 <= ease <= 12: "ok" (Mos)
      12 < ease <= 20: "loose" (Erkin)
      ease > 20: "oversize" (Oversize)
    """
    size_upper = size.upper()
    if size_upper not in SIZE_CHART:
        size_upper = "M"

    garment = SIZE_CHART[size_upper]
    zone_boxes = compute_zone_boxes(landmarks)

    # 1. Har zona bo'yicha ease va holatni hisoblash
    zones_data = {}

    # A) Yelka (shoulder width diff x 2 orqali moslashtirilgan ease)
    sh_garment_w = garment["shoulder_width"]
    sh_body_w = body["shoulder_cm"]
    sh_ease = round((sh_garment_w - sh_body_w) * 2.0, 1)
    zones_data["shoulder"] = _evaluate_zone("Yelka", sh_ease, sh_body_w, sh_garment_w, zone_boxes.get("shoulder"), is_width=True)

    # B) Ko'krak (chest circumference)
    ch_garment_circ = garment["chest_width"] * 2.0
    ch_body_circ = body["chest_cm"]
    ch_ease = round(ch_garment_circ - ch_body_circ, 1)
    zones_data["chest"] = _evaluate_zone("Ko'krak", ch_ease, ch_body_circ, ch_garment_circ, zone_boxes.get("chest"))

    # C) Bel (waist circumference)
    w_garment_circ = garment["waist_width"] * 2.0
    w_body_circ = body["waist_cm"]
    w_ease = round(w_garment_circ - w_body_circ, 1)
    zones_data["waist"] = _evaluate_zone("Bel", w_ease, w_body_circ, w_garment_circ, zone_boxes.get("waist"))

    # D) Bo'ksa (hip circumference)
    h_garment_circ = garment["hip_width"] * 2.0
    h_body_circ = body["hip_cm"]
    h_ease = round(h_garment_circ - h_body_circ, 1)
    zones_data["hip"] = _evaluate_zone("Bo'ksa", h_ease, h_body_circ, h_garment_circ, zone_boxes.get("hip"))

    # 2. Umumiy fit_score (0-100) va fit_label
    zone_scores = []
    has_tight = False
    has_oversize = False
    max_severity = 0

    for z_key, z_val in zones_data.items():
        st = z_val["status"]
        ease_val = z_val["ease"]
        sev = z_val["severity"]

        if st == "tight":
            has_tight = True
            max_severity = max(max_severity, sev)
            z_score = max(15.0, 75.0 - sev * 0.7)
        elif st == "ok":
            # 8 sm ideal ease
            z_score = max(88.0, 100.0 - abs(ease_val - 8.0) * 2.2)
        elif st == "loose":
            z_score = max(70.0, 85.0 - (ease_val - 12.0) * 1.5)
        else:  # oversize
            has_oversize = True
            z_score = max(50.0, 70.0 - (ease_val - 20.0) * 1.0)

        zone_scores.append(z_score)

    avg_score = int(round(float(np.mean(zone_scores))))

    if has_tight:
        fit_score = max(20, min(65, avg_score))
        fit_label = "Tor"
    elif all(z["status"] == "ok" for z in zones_data.values()):
        fit_score = max(90, min(99, avg_score))
        fit_label = "Mos"
    elif has_oversize:
        fit_score = max(60, min(80, avg_score))
        fit_label = "Oversize"
    else:
        fit_score = max(75, min(88, avg_score))
        fit_label = "Erkin"

    # 3. Eng mos tavsiya etilgan o'lcham (recommended_size)
    recommended_size = _find_best_size(body)

    # 4. Qisqa izoh (summary)
    if fit_label == "Tor":
        tight_zones = [z["name"] for z in zones_data.values() if z["status"] == "tight"]
        zones_str = ", ".join(tight_zones)
        summary = f"{size_upper} o'lchami {zones_str} sohasida torlik qiladi. Kattaroq o'lcham ({recommended_size}) tavsiya etiladi."
    elif fit_label == "Mos":
        summary = f"{size_upper} o'lchami qomatingizga ideal mos tushadi (erkin harakatlanish uchun qulay)."
    elif fit_label == "Oversize":
        summary = f"{size_upper} o'lchami ancha katta bo'lib, zamonaviy oversize uslubida erkin tushib turadi."
    else:
        summary = f"{size_upper} o'lchami biroz keng va qulay, erkin kiyishni xush ko'ruvchilar uchun mos."

    return {
        "selected_size": size_upper,
        "recommended_size": recommended_size,
        "fit_score": fit_score,
        "fit_label": fit_label,
        "summary": summary,
        "zones": zones_data
    }

def _evaluate_zone(name: str, ease: float, body_val: float, garment_val: float, box: dict, is_width: bool = False) -> dict:
    """
    Bitta zona bo'yicha status, severity va o'zbekcha izohni qaytaradi.
    """
    if ease < 4.0:
        status = "tight"
        label = "Tor"
        tight_cm = round(4.0 - ease, 1)
        # Severity 0-100: ease qancha kichik bo'lsa shuncha yuqori
        severity = min(100, max(25, int(30 + tight_cm * 14)))
        note = f"{tight_cm} sm tor (siqib turadi)"
    elif 4.0 <= ease <= 12.0:
        status = "ok"
        label = "Mos"
        severity = 0
        note = f"{ease} sm qulay erkinlik (ideal)"
    elif 12.0 < ease <= 20.0:
        status = "loose"
        label = "Erkin"
        severity = 0
        note = f"{ease} sm keng (erkin tushadi)"
    else:
        status = "oversize"
        label = "Oversize"
        severity = 0
        note = f"{ease} sm juda keng (oversize)"

    return {
        "name": name,
        "status": status,
        "label": label,
        "ease": ease,
        "severity": severity,
        "body_cm": body_val,
        "garment_cm": garment_val,
        "is_width": is_width,
        "note": note,
        "box": box or {"x": 0, "y": 0, "width": 0, "height": 0}
    }

def _find_best_size(body: dict) -> str:
    """
    Barcha o'lchamlar orasidan hech bir zona tor bo'lmagan va ideal qulaylikka
    eng yaqin o'lchamni tanlaydi.
    """
    best_size = "M"
    best_score = -float('inf')

    for sz in ORDERED_SIZES:
        g = SIZE_CHART[sz]
        sh_ease = (g["shoulder_width"] - body["shoulder_cm"]) * 2.0
        ch_ease = g["chest_width"] * 2.0 - body["chest_cm"]
        w_ease = g["waist_width"] * 2.0 - body["waist_cm"]
        h_ease = g["hip_width"] * 2.0 - body["hip_cm"]

        eases = [sh_ease, ch_ease, w_ease, h_ease]
        min_ease = min(eases)

        # Agar barcha zonalar ease >= 4.0 (tor emas) bo'lsa
        if min_ease >= 4.0:
            closeness = -sum(abs(e - 8.0) for e in eases)
            if closeness > best_score:
                best_score = closeness
                best_size = sz

    if best_score == -float('inf'):
        # Agar barcha o'lchamlar tor bo'lsa, eng kattasini (XXL) tavsiya qilish
        best_size = "XXL"

    return best_size
