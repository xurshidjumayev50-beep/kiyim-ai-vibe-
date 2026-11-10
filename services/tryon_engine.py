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

    def extract_clean_garment(self, img: np.ndarray):
        """
        Kiyim rasmidan fonni to'liq tozalab, kiyimning haqiqiy chegarasini ajratib oladi.
        """
        h, w = img.shape[:2]
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

        crop_garm = img[gy:gy+gh, gx:gx+gw]
        crop_mask = clean_mask[gy:gy+gh, gx:gx+gw]
        return crop_garm, crop_mask

    def generate_fabric_folds(self, h: int, w: int, fit_mode: str) -> np.ndarray:
        """
        O'lchamga qarab kiyimga tabiiy mato burmalari va soyalarini qo'shadi:
        - Tor (Tight): Gorizontal taranglik chiziqlari (tension wrinkles)
        - Katta (Loose/Oversized): Vertikal osilib turuvchi gravitatsion burmalar
        - Ideal (Perfect): Silliq anatomik qomat soyasi
        """
        fold_layer = np.ones((h, w), dtype=np.float32)

        if fit_mode == "tight":
            # Tor kiyimda ko'krak va qorin bo'ylab gorizontal taranglik
            for y_rel in [0.35, 0.48, 0.62, 0.75]:
                cy = int(h * y_rel)
                y_indices = np.arange(max(0, cy - 8), min(h, cy + 9))
                intensity = np.sin((y_indices - (cy - 8)) / 16.0 * np.pi) * 0.12
                fold_layer[y_indices, :] -= intensity[:, np.newaxis]

        elif fit_mode == "loose":
            # Oversized kiyimda yelkalardan pastga osilib tushuvchi vertikal burmalar
            for x_rel in [0.22, 0.38, 0.62, 0.78]:
                cx = int(w * x_rel)
                x_indices = np.arange(max(0, cx - 14), min(w, cx + 15))
                intensity = np.sin((x_indices - (cx - 14)) / 28.0 * np.pi) * 0.16
                fold_layer[:, x_indices] -= intensity[np.newaxis, :]
        else:
            y_grad = np.linspace(0.96, 1.04, h)[:, np.newaxis]
            fold_layer = fold_layer * y_grad

        return np.clip(fold_layer, 0.75, 1.25)

    def try_replicate_cloud_vton(self, person_path: str, garment_path: str, output_path: str) -> bool:
        """
        Agar REPLICATE_API_TOKEN mavjud bo'lsa, IDM-VTON bulutli diffusion modelini chaqiradi.
        """
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not api_token:
            return False

        try:
            with open(person_path, "rb") as f:
                user_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
            with open(garment_path, "rb") as f:
                garm_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            body = {
                "version": "c871bb9b046616b68044220de00f12165bbf3176bc2f644bb3f3779b33c1fb29", # IDM-VTON
                "input": {
                    "human_img": user_b64,
                    "garm_img": garm_b64,
                    "category": "upper_body"
                }
            }

            resp = requests.post("https://api.replicate.com/v1/predictions", json=body, headers=headers, timeout=20)
            if resp.status_code in [200, 201]:
                prediction = resp.json()
                poll_url = prediction.get("urls", {}).get("get")
                import time
                for _ in range(30):
                    time.sleep(2)
                    poll_res = requests.get(poll_url, headers=headers, timeout=10).json()
                    status = poll_res.get("status")
                    if status == "succeeded":
                        out_url = poll_res.get("output")
                        if isinstance(out_url, list):
                            out_url = out_url[0]
                        img_data = requests.get(out_url, timeout=15).content
                        with open(output_path, "wb") as f_out:
                            f_out.write(img_data)
                        return True
                    elif status in ["failed", "canceled"]:
                        break
        except Exception as e:
            print(f"Replicate VTON chaqirishda xatolik: {e}")
        return False

    def overlay_garment(self, person_path: str, garment_path: str, output_path: str, fit_mode: str = "perfect") -> str:
        """
        Kiyimni foydalanuvchining ustiga to'liq kiydirilgan (Fully Dressed) holatda kiygizadi:
        - Butun yuqori qism (yelkalar, ko'krak, qorin va yenglar) to'liq yangi kiyim bilan qoplanadi;
        - Eski kiyim/futbolka butunlay yopiladi;
        - Bosh, bo'yin va qo'llar tabiiy saqlanadi;
        - O'lcham (Tor / Ideal / Katta) ga qarab tana konturida deformatsiya qilinadi.
        """
        # 1. Bulutli Replicate IDM-VTON tekshirish
        if self.try_replicate_cloud_vton(person_path, garment_path, output_path):
            return output_path

        # 2. Mahalliy Anatomik To'liq Kiyintirish Dvigateli (Local Full-Body Dressing Engine)
        person = cv2.imread(person_path)
        garment = cv2.imread(garment_path)

        if person is None or garment is None:
            raise ValueError("Rasm fayllarini ochib bo'lmadi")

        H, W = person.shape[:2]

        has_pose = False
        body_mask = None
        if self.detector:
            try:
                mp_img = mp.Image.create_from_file(person_path)
                res = self.detector.detect(mp_img)
                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    lm = res.pose_landmarks[0]
                    ls = np.array([lm[11].x * W, lm[11].y * H]) # Chap yelka
                    rs = np.array([lm[12].x * W, lm[12].y * H]) # O'ng yelka
                    le = np.array([lm[13].x * W, lm[13].y * H]) # Chap tirsak
                    re = np.array([lm[14].x * W, lm[14].y * H]) # O'ng tirsak
                    lh = np.array([lm[23].x * W, lm[23].y * H]) # Chap son/bel
                    rh = np.array([lm[24].x * W, lm[24].y * H]) # O'ng son/bel
                    nose = np.array([lm[0].x * W, lm[0].y * H]) # Burun
                    
                    if res.segmentation_masks and len(res.segmentation_masks) > 0:
                        seg = res.segmentation_masks[0].numpy_view()[:, :, 0]
                        body_mask = (seg > 0.35).astype(np.uint8) * 255
                    has_pose = True
            except Exception as e:
                print(f"Pose aniqlashda xatolik: {e}")

        # Fallback agar MediaPipe aniqlay olmasa
        if not has_pose:
            rs = np.array([W * 0.28, H * 0.35])
            ls = np.array([W * 0.72, H * 0.35])
            re = np.array([W * 0.20, H * 0.60])
            le = np.array([W * 0.80, H * 0.60])
            rh = np.array([W * 0.35, H * 0.75])
            lh = np.array([W * 0.65, H * 0.75])
            nose = np.array([W * 0.50, H * 0.18])

        # Kiyim rasmidan fonni tozalash
        crop_garm, crop_mask = self.extract_clean_garment(garment)
        gh, gw = crop_garm.shape[:2]

        shoulder_dist = np.linalg.norm(ls - rs)
        torso_height = np.linalg.norm(((lh + rh) / 2.0) - ((ls + rs) / 2.0))

        # O'lcham deformatsiyasi koeffitsientlari (Size & Fit)
        if fit_mode == "tight":
            w_mult = 0.93
            h_mult = 0.94
        elif fit_mode == "loose":
            w_mult = 1.22
            h_mult = 1.15
        else:
            w_mult = 1.05
            h_mult = 1.02

        # Insonning tana va yenglarini to'liq qamrab oluvchi to'rttala chegara nuqtalari
        # Top-left (o'ng yelka va tirsakdan tashqariroq)
        top_left_x = min(rs[0], re[0]) - 30 * w_mult
        top_right_x = max(ls[0], le[0]) + 30 * w_mult
        top_y = min(rs[1], ls[1]) - 40

        bottom_left_x = min(rh[0], re[0]) - 20 * w_mult
        bottom_right_x = max(lh[0], le[0]) + 20 * w_mult
        bottom_y = max(rh[1], lh[1]) + 50 * h_mult

        src_pts = np.float32([[0, 0], [gw, 0], [gw, gh], [0, gh]])
        dst_pts = np.float32([
            [top_left_x, top_y],
            [top_right_x, top_y],
            [bottom_right_x, bottom_y],
            [bottom_left_x, bottom_y]
        ])

        # Perspektiv deformatsiya
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_garm = cv2.warpPerspective(crop_garm, M, (W, H), flags=cv2.INTER_LINEAR)
        warped_mask = cv2.warpPerspective(crop_mask, M, (W, H), flags=cv2.INTER_LINEAR)

        # Yuqori tana kiyim zonasini aniqlash (Insonning butun ko'krak, yelka va yeng qismi)
        if body_mask is None:
            body_mask = np.ones((H, W), dtype=np.uint8) * 255

        clothing_zone = np.zeros((H, W), dtype=np.uint8)
        min_x = max(0, int(min(top_left_x, bottom_left_x)))
        max_x = min(W, int(max(top_right_x, bottom_right_x)))
        min_y = max(0, int(top_y))
        max_y = min(H, int(bottom_y))
        clothing_zone[min_y:max_y, min_x:max_x] = 255

        # Inson tanasining yuqori kiyim kiyiladigan qismi
        upper_body_mask = cv2.bitwise_and(body_mask, clothing_zone)

        # Bosh va iyak qismini himoyalash (yoqa bo'yin tagida to'g'ri o'tirishi uchun)
        head_r = int(shoulder_dist * 0.34)
        cv2.circle(upper_body_mask, (int(nose[0]), int(nose[1])), head_r, 0, -1)

        # Yangi kiyimning to'liq qoplovchi maskasi
        # warped_mask va inson tanasining kesishmasi
        dress_mask = cv2.bitwise_and(warped_mask, upper_body_mask)

        # Chekka qirralarni yumshatish (anti-aliasing)
        dress_mask_f = cv2.GaussianBlur(dress_mask, (5, 5), 0) / 255.0
        mask_3d = np.repeat(dress_mask_f[:, :, np.newaxis], 3, axis=2)

        # Fotometrik yorug'lik va soyalarni inson tanasidan yangi kiyimga singdirish
        gray_user = cv2.cvtColor(person, cv2.COLOR_BGR2GRAY)
        blur_lighting = cv2.bilateralFilter(gray_user, 9, 75, 75)
        ambient_light = np.clip(blur_lighting.astype(float) / 125.0, 0.72, 1.28)
        
        # O'lchamga mos mato burmalari
        folds = self.generate_fabric_folds(H, W, fit_mode)
        combined_shading = np.repeat((ambient_light * folds)[:, :, np.newaxis], 3, axis=2)

        shaded_garm = np.clip(warped_garm.astype(float) * combined_shading, 0, 255).astype(np.uint8)

        # Inson tanasiga to'liq kiydirish (Full Composite)
        result = (person.astype(float) * (1.0 - mask_3d) + shaded_garm.astype(float) * mask_3d).astype(np.uint8)

        cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 94])
        return output_path

tryon_engine = TryOnEngine()
