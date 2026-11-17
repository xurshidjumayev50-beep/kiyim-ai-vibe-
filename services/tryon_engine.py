import os
import cv2
import numpy as np
import base64
import requests
import json

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except Exception as e:
    HAS_MEDIAPIPE = False
    print(f"MediaPipe yuklanmadi (Fallback rejimida ishlaydi): {e}")

# Gemini rasm generatsiyasi uchun maxsus prompt
GEMINI_TRYON_PROMPT = (
    "Birinchi rasmdagi odamni oling. Uning yuzi, sochi, pozasi, qo'llari, fon va yorug'ligi aynan o'zgarishsiz qolsin. "
    "Ikkinchi rasmdagi kiyimni shu odamning tanasiga kiydiring. Faqat kiyimni almashtiring. "
    "Ikkinchi rasmdagi ilgich, maneken, bo'yin tayanchi, fon yoki aksessuarlarni ko'chirmang. "
    "Odamning o'z bo'yni, yoqasi va ko'ylagi yoqasi tabiiy ko'rinsin. "
    "Kiyim yelka va ko'krak chizig'iga tabiiy tushsin, burma va soyalar yorug'likka mos bo'lsin. "
    "Tanlangan o'lcham: {size}."
)

class TryOnEngine:
    def __init__(self):
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "pose_landmarker_lite.task"
        )
        self.detector = None
        if HAS_MEDIAPIPE and os.path.exists(self.model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=True)
                self.detector = vision.PoseLandmarker.create_from_options(options)
            except Exception as e:
                print(f"MediaPipe Pose yuklashda xatolik: {e}")

    def clean_and_isolate_garment(self, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Kiyim rasmidan fonni tozalaydi, ilgich (hanger) va maneken bo'yin detallarini
        butunlay kesib tashlaydi, kiyimni toza oq fonga o'tkazadi.
        """
        h, w = img.shape[:2]

        # 1. Fon rangini aniqlash (chegaralar bo'yicha)
        border = np.concatenate([
            img[:15, :].reshape(-1, 3),
            img[-15:, :].reshape(-1, 3),
            img[:, :15].reshape(-1, 3),
            img[:, -15:].reshape(-1, 3)
        ])
        bg_median = np.median(border, axis=0)
        diff = np.linalg.norm(img.astype(float) - bg_median, axis=2)

        thresh_val = max(18.0, np.percentile(diff[diff < 50], 85) if np.any(diff < 50) else 22.0)
        raw_mask = (diff > thresh_val).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        closed_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel, iterations=3)

        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        if contours:
            c = max(contours, key=cv2.contourArea)
            cv2.drawContours(clean_mask, [c], -1, 255, -1)
            gx, gy, gw, gh = cv2.boundingRect(c)
        else:
            gx, gy, gw, gh = 0, 0, w, h
            clean_mask[:] = 255

        # 2. Ilgich va maneken tayanchini (Hanger / Mannequin neck) aniqlash va kesib tashlash
        # Ilgich yoki maneken odatda kiyimning tepa markazida joylashadi
        col_sums = np.sum(clean_mask > 0, axis=0)
        max_col_w = np.max(col_sums) if np.max(col_sums) > 0 else 1

        row_widths = np.sum(clean_mask[gy:gy+gh, gx:gx+gw] > 0, axis=1)
        max_w = np.max(row_widths) if len(row_widths) > 0 and np.max(row_widths) > 0 else gw

        # Yuqori qismda kengligi kiyimning maksimal kengligidan sezilarli tor bo'lgan
        # ilgich qismini (odatda < 38% kenglik) topish
        cut_offset = 0
        top_quarter = int(gh * 0.28)
        for r_idx in range(min(top_quarter, len(row_widths))):
            curr_w = row_widths[r_idx]
            # Agar yuqori qatordagi kenglik tor bo'lsa (ilgich yoki maneken bo'yni)
            if curr_w < max_w * 0.40:
                cut_offset = r_idx + 1
            else:
                break

        # Qo'shimcha xavfsizlik: ilgich izini to'liq olib tashlash uchun 4-8 piksel chuqurroq kesish
        if cut_offset > 0:
            cut_offset = min(int(gh * 0.25), cut_offset + 6)
            clean_mask[:gy+cut_offset, :] = 0
            gy += cut_offset
            gh = max(10, gh - cut_offset)

        # 3. Kiyimni toza oq fonga o'tkazish
        crop_garm = img[gy:gy+gh, gx:gx+gw].copy()
        crop_mask = clean_mask[gy:gy+gh, gx:gx+gw].copy()

        # Maskaning chetlarini tekislash
        mask_3d = np.repeat((crop_mask / 255.0)[:, :, np.newaxis], 3, axis=2)
        white_bg = np.ones_like(crop_garm) * 255
        clean_garm_white = (crop_garm * mask_3d + white_bg * (1.0 - mask_3d)).astype(np.uint8)

        return clean_garm_white, crop_mask

    def try_gemini_vton(self, person_bytes: bytes, garment_bytes: bytes, size: str = "M") -> bytes | None:
        """
        Gemini AI orqali rasm generatsiyasini amalga oshirish:
        Berilgan prompt bo'yicha odam va kiyim rasmini tahlil qilib, generatsiya qiladi.
        API kalit faqat server muhitida (GEMINI_API_KEY yoki GOOGLE_API_KEY).
        """
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None

        prompt = GEMINI_TRYON_PROMPT.format(size=size)

        try:
            # Kiyim rasmini toza oq fonga o'tkazish va ilgich/maneken qismini kesib tashlash
            garment_img = cv2.imdecode(np.frombuffer(garment_bytes, np.uint8), cv2.IMREAD_COLOR)
            if garment_img is not None:
                clean_garm, _ = self.clean_and_isolate_garment(garment_img)
                ok, enc = cv2.imencode(".jpg", clean_garm, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if ok:
                    garment_bytes = enc.tobytes()

            person_b64 = base64.b64encode(person_bytes).decode("utf-8")
            garment_b64 = base64.b64encode(garment_bytes).decode("utf-8")

            # Google Gemini REST API orqali multimodal so'rov
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": person_b64
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": garment_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                }
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=40)
            if resp.status_code == 200:
                result_json = resp.json()
                # Agar Gemini rasm (inline_data) qaytargan bo'lsa
                candidates = result_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inline_data" in part and part["inline_data"].get("data"):
                            return base64.b64decode(part["inline_data"]["data"])
        except Exception as e:
            print(f"[Gemini VTON] Xatolik: {e}")

        return None

    def generate_fabric_folds(self, h: int, w: int, fit_mode: str) -> np.ndarray:
        """
        O'lchamga qarab tabiiy mato burmalari va soyalarini hisoblaydi:
        - Tor: Gorizontal taranglik burmalari
        - Katta / Erkin: Vertikal osilib tushuvchi burmalar
        - Mos: Silliq anatomik qomat soyasi
        """
        fold_layer = np.ones((h, w), dtype=np.float32)

        if fit_mode == "tight":
            for y_rel in [0.38, 0.52, 0.68]:
                cy = int(h * y_rel)
                y_indices = np.arange(max(0, cy - 8), min(h, cy + 9))
                intensity = np.sin((y_indices - (cy - 8)) / 16.0 * np.pi) * 0.10
                fold_layer[y_indices, :] -= intensity[:, np.newaxis]
        elif fit_mode in ("loose", "oversize"):
            for x_rel in [0.25, 0.40, 0.60, 0.75]:
                cx = int(w * x_rel)
                x_indices = np.arange(max(0, cx - 12), min(w, cx + 13))
                intensity = np.sin((x_indices - (cx - 12)) / 24.0 * np.pi) * 0.12
                fold_layer[:, x_indices] -= intensity[np.newaxis, :]
        else:
            y_grad = np.linspace(0.97, 1.03, h)[:, np.newaxis]
            fold_layer = fold_layer * y_grad

        return np.clip(fold_layer, 0.80, 1.20)

    def overlay_garment_in_memory(self, person_bytes: bytes, garment_bytes: bytes, size: str = "M", fit_mode: str = "perfect") -> bytes:
        """
        Kiyimni odam tanasiga anatomik moslashtirib kiydiradi.
        Barcha operatsiyalar xotirada bajariladi, server diskida hech narsa saqlanmaydi.
        Natija JPEG baytlari sifatida qaytadi.
        """
        # 1. Gemini bilan sinab ko'rish
        gemini_result = self.try_gemini_vton(person_bytes, garment_bytes, size=size)
        if gemini_result:
            return gemini_result

        # 2. Mahalliy anatomik kiyintirish dvigateli
        person = cv2.imdecode(np.frombuffer(person_bytes, np.uint8), cv2.IMREAD_COLOR)
        garment = cv2.imdecode(np.frombuffer(garment_bytes, np.uint8), cv2.IMREAD_COLOR)

        if person is None or garment is None:
            raise ValueError("Rasm ma'lumotlarini o'qib bo'lmadi")

        H, W = person.shape[:2]

        # MediaPipe Pose orqali odam qomatini aniqlash
        has_pose = False
        body_mask = None

        if self.detector:
            try:
                rgb_person = cv2.cvtColor(person, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_person)
                res = self.detector.detect(mp_img)
                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    lm = res.pose_landmarks[0]
                    ls = np.array([lm[11].x * W, lm[11].y * H]) # Chap yelka
                    rs = np.array([lm[12].x * W, lm[12].y * H]) # O'ng yelka
                    le = np.array([lm[13].x * W, lm[13].y * H]) # Chap tirsak
                    re = np.array([lm[14].x * W, lm[14].y * H]) # O'ng tirsak
                    lh = np.array([lm[23].x * W, lm[23].y * H]) # Chap son
                    rh = np.array([lm[24].x * W, lm[24].y * H]) # O'ng son
                    nose = np.array([lm[0].x * W, lm[0].y * H]) # Burun

                    if res.segmentation_masks and len(res.segmentation_masks) > 0:
                        seg = res.segmentation_masks[0].numpy_view()[:, :, 0]
                        body_mask = (seg > 0.35).astype(np.uint8) * 255
                    has_pose = True
            except Exception as e:
                print(f"Pose aniqlashda xatolik: {e}")

        if not has_pose:
            rs = np.array([W * 0.28, H * 0.34])
            ls = np.array([W * 0.72, H * 0.34])
            re = np.array([W * 0.20, H * 0.60])
            le = np.array([W * 0.80, H * 0.60])
            rh = np.array([W * 0.35, H * 0.75])
            lh = np.array([W * 0.65, H * 0.75])
            nose = np.array([W * 0.50, H * 0.18])

        # Kiyimdan ilgich/maneken va fonni tozalash
        crop_garm, crop_mask = self.clean_and_isolate_garment(garment)
        gh, gw = crop_garm.shape[:2]

        shoulder_dist = np.linalg.norm(ls - rs)
        neck_center = (ls + rs) / 2.0

        # O'lchamga mos koeffitsientlar
        if fit_mode == "tight":
            w_mult = 0.95
            h_mult = 0.96
        elif fit_mode in ("loose", "oversize"):
            w_mult = 1.18
            h_mult = 1.10
        else:
            w_mult = 1.04
            h_mult = 1.02

        # Yelka va ko'krak chizig'iga tabiiy moslashtirish:
        # Kiyim yoqasini odamning bo'yin poydevoriga to'g'ri o'rnatish
        top_left_x = min(rs[0], re[0]) - 16 * w_mult
        top_right_x = max(ls[0], le[0]) + 16 * w_mult
        top_y = min(rs[1], ls[1]) - 10  # Yoqa odamning bo'ynidan tepaga chiqib ketmaydi

        bottom_left_x = min(rh[0], re[0]) - 12 * w_mult
        bottom_right_x = max(lh[0], le[0]) + 12 * w_mult
        bottom_y = max(rh[1], lh[1]) + 40 * h_mult

        src_pts = np.float32([[0, 0], [gw, 0], [gw, gh], [0, gh]])
        dst_pts = np.float32([
            [top_left_x, top_y],
            [top_right_x, top_y],
            [bottom_right_x, bottom_y],
            [bottom_left_x, bottom_y]
        ])

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_garm = cv2.warpPerspective(crop_garm, M, (W, H), flags=cv2.INTER_LINEAR)
        warped_mask = cv2.warpPerspective(crop_mask, M, (W, H), flags=cv2.INTER_LINEAR)

        # Odam tanasi yuqori kiyim zonasini aniqlash
        if body_mask is None:
            body_mask = np.ones((H, W), dtype=np.uint8) * 255

        clothing_zone = np.zeros((H, W), dtype=np.uint8)
        min_x = max(0, int(min(top_left_x, bottom_left_x)))
        max_x = min(W, int(max(top_right_x, bottom_right_x)))
        min_y = max(0, int(top_y))
        max_y = min(H, int(bottom_y))
        clothing_zone[min_y:max_y, min_x:max_x] = 255

        upper_body_mask = cv2.bitwise_and(body_mask, clothing_zone)

        # Odamning o'z yuzi, iyak va bo'yin qismini himoyalash
        # (Kiyim bo'yinga yoki yuzga chiqib ketmasligi va o'z yoqasi tabiiy ko'rinishi uchun)
        head_r = int(shoulder_dist * 0.32)
        cv2.circle(upper_body_mask, (int(nose[0]), int(nose[1])), head_r, 0, -1)

        neck_w = int(shoulder_dist * 0.22)
        neck_top = int(nose[1] + head_r * 0.6)
        neck_bot = int(neck_center[1] - 4)
        if neck_bot > neck_top:
            cv2.rectangle(
                upper_body_mask,
                (int(neck_center[0] - neck_w), neck_top),
                (int(neck_center[0] + neck_w), neck_bot),
                0, -1
            )

        dress_mask = cv2.bitwise_and(warped_mask, upper_body_mask)
        dress_mask_f = cv2.GaussianBlur(dress_mask, (5, 5), 0) / 255.0
        mask_3d = np.repeat(dress_mask_f[:, :, np.newaxis], 3, axis=2)

        # Yorug'lik va tabiiy burmalarni tushirish
        gray_user = cv2.cvtColor(person, cv2.COLOR_BGR2GRAY)
        blur_lighting = cv2.bilateralFilter(gray_user, 9, 75, 75)
        ambient_light = np.clip(blur_lighting.astype(float) / 125.0, 0.75, 1.25)

        folds = self.generate_fabric_folds(H, W, fit_mode)
        combined_shading = np.repeat((ambient_light * folds)[:, :, np.newaxis], 3, axis=2)

        shaded_garm = np.clip(warped_garm.astype(float) * combined_shading, 0, 255).astype(np.uint8)

        # Inson tanasiga kompozit qilish
        result = (person.astype(float) * (1.0 - mask_3d) + shaded_garm.astype(float) * mask_3d).astype(np.uint8)

        # Xotirada JPEG formatga kodlash
        success, encoded_jpg = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 93])
        if not success:
            raise RuntimeError("Natijani JPEG ga kodlashda xatolik")

        return encoded_jpg.tobytes()

tryon_engine = TryOnEngine()
