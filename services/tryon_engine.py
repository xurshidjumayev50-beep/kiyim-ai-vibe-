import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class TryOnEngine:
    def __init__(self):
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "pose_landmarker_lite.task"
        )
        self.detector = None
        if os.path.exists(self.model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=True)
                self.detector = vision.PoseLandmarker.create_from_options(options)
            except Exception as e:
                print(f"MediaPipe Pose yuklashda xatolik: {e}")

    def extract_clean_garment(self, img: np.ndarray):
        """
        Kiyim rasmidan orqa fonni (oq, kulrang yoki studiya fonini) to'liq tozalab,
        kiyimning haqiqiy chegarasini aniqlaydi.
        """
        h, w = img.shape[:2]
        # Chekka piksellardan fon rangini aniqlash
        border = np.concatenate([
            img[:15, :].reshape(-1, 3),
            img[-15:, :].reshape(-1, 3),
            img[:, :15].reshape(-1, 3),
            img[:, -15:].reshape(-1, 3)
        ])
        bg_median = np.median(border, axis=0)
        diff = np.linalg.norm(img.astype(float) - bg_median, axis=2)
        
        # Ostonaviy farq
        thresh_val = max(18.0, np.percentile(diff[diff < 50], 85) if np.any(diff < 50) else 22.0)
        raw_mask = (diff > thresh_val).astype(np.uint8) * 255
        
        # Kiyim ichidagi yorug' qismlarni (logotip, oq chiziqlar) to'ldirish
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

    def generate_fabric_folds(self, h: int, w: int, fit_mode: str, shoulder_dist: float) -> np.ndarray:
        """
        O'lchamga qarab kiyimga tabiiy mato burmalari va soyalarini hosil qiladi:
        - Tor (Tight): Ko'krak va qorin bo'ylab gorizontal taranglik (tension) burmalari
        - Katta (Loose/Oversized): Yelkalardan pastga osilib tushuvchi vertikal gravitatsion burmalar
        - Ideal (Perfect): Yumshoq anatomik tana soyasi
        """
        fold_layer = np.ones((h, w), dtype=np.float32)

        if fit_mode == "tight":
            # Gorizontal taranglik chiziqlari (tarang kiyim tanani siqganda hosil bo'ladi)
            for y_rel in [0.35, 0.48, 0.62, 0.75]:
                cy = int(h * y_rel)
                y_indices = np.arange(max(0, cy - 8), min(h, cy + 9))
                intensity = np.sin((y_indices - (cy - 8)) / 16.0 * np.pi) * 0.12
                fold_layer[y_indices, :] -= intensity[:, np.newaxis]

        elif fit_mode == "loose":
            # Vertikal osilib turuvchi gravitatsion burmalar (oversized kiyimlar uchun)
            for x_rel in [0.22, 0.38, 0.62, 0.78]:
                cx = int(w * x_rel)
                x_indices = np.arange(max(0, cx - 14), min(w, cx + 15))
                intensity = np.sin((x_indices - (cx - 14)) / 28.0 * np.pi) * 0.16
                fold_layer[:, x_indices] -= intensity[np.newaxis, :]
        else:
            # Standart yumshoq qomat soyasi
            y_grad = np.linspace(0.95, 1.05, h)[:, np.newaxis]
            fold_layer = fold_layer * y_grad

        return np.clip(fold_layer, 0.75, 1.25)

    def overlay_garment(self, person_path: str, garment_path: str, output_path: str, fit_mode: str = "perfect") -> str:
        """
        Kiyimni foydalanuvchining tana tuzilishi, yelka burchagi, bo'yi va o'lchamiga
        to'liq moslashtirib (Perspective Mesh Warp + Photometric Relighting) kiyintiradi.
        """
        person = cv2.imread(person_path)
        garment = cv2.imread(garment_path)

        if person is None or garment is None:
            raise ValueError("Rasm fayllarini ochib bo'lmadi")

        H, W = person.shape[:2]

        # 1. MediaPipe orqali tana skeletini va nuqtalarini aniqlash
        has_pose = False
        if self.detector:
            try:
                mp_img = mp.Image.create_from_file(person_path)
                res = self.detector.detect(mp_img)
                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    lm = res.pose_landmarks[0]
                    ls = np.array([lm[11].x * W, lm[11].y * H]) # Chap yelka (rasmda o'ngda)
                    rs = np.array([lm[12].x * W, lm[12].y * H]) # O'ng yelka (rasmda chapda)
                    lh = np.array([lm[23].x * W, lm[23].y * H]) # Chap son / bel
                    rh = np.array([lm[24].x * W, lm[24].y * H]) # O'ng son / bel
                    nose = np.array([lm[0].x * W, lm[0].y * H])
                    has_pose = True
            except Exception as e:
                print(f"Pose aniqlashda xatolik: {e}")

        # Agar mediapipe bo'lmasa yoki tana to'liq ko'rinmasa, fallback parametrlar
        if not has_pose:
            rs = np.array([W * 0.28, H * 0.35])
            ls = np.array([W * 0.72, H * 0.35])
            rh = np.array([W * 0.35, H * 0.75])
            lh = np.array([W * 0.65, H * 0.75])
            nose = np.array([W * 0.50, H * 0.18])

        # 2. Kiyimni tozalab qirqib olish
        crop_garm, crop_mask = self.extract_clean_garment(garment)
        gh, gw = crop_garm.shape[:2]

        # 3. Tana proporsiyalari
        mid_shoulder = (ls + rs) / 2.0
        mid_hip = (lh + rh) / 2.0
        shoulder_dist = np.linalg.norm(ls - rs)
        torso_height = np.linalg.norm(mid_hip - mid_shoulder)

        # 4. O'lchamga qarab tana ustidagi kiyim deformatsiyasi (Size & Fit Integration):
        # - Tight: yelkalar va bel qisilgan, ko'ylak qisqaroq
        # - Loose: yelkalar pastga tushgan (drop-shoulder), bel keng va osilgan, etagi uzun
        # - Perfect: ideal mutanosiblik
        if fit_mode == "tight":
            w_shoulder_scale = 0.92
            w_waist_scale = 0.88
            h_scale = 0.94
        elif fit_mode == "loose":
            w_shoulder_scale = 1.24  # Drop-shoulder effekti
            w_waist_scale = 1.28     # Keng osilib turishi
            h_scale = 1.16           # Uzunroq etak
        else:
            w_shoulder_scale = 1.05
            w_waist_scale = 1.02
            h_scale = 1.03

        # Yelka yo'nalish vektori va unga perpendikulyar vektor (yoqa balandligi uchun)
        shoulder_vec = ls - rs
        dir_s = shoulder_vec / (np.linalg.norm(shoulder_vec) + 1e-6)
        perp_s = np.array([-dir_s[1], dir_s[0]]) # Yuqoriga yo'nalish

        top_y_offset = shoulder_dist * 0.14

        # Maqsadli nuqtalar (Target Quad Points):
        dst_top_left = rs - dir_s * (shoulder_dist * 0.24 * w_shoulder_scale) - perp_s * top_y_offset
        dst_top_right = ls + dir_s * (shoulder_dist * 0.24 * w_shoulder_scale) - perp_s * top_y_offset

        hip_vec = lh - rh
        dir_h = hip_vec / (np.linalg.norm(hip_vec) + 1e-6)
        
        dst_bottom_left = rh - dir_h * (shoulder_dist * 0.20 * w_waist_scale) + np.array([0, torso_height * 0.22 * h_scale])
        dst_bottom_right = lh + dir_h * (shoulder_dist * 0.20 * w_waist_scale) + np.array([0, torso_height * 0.22 * h_scale])

        # Perspektiv matritsa (Perspective Transform)
        src_pts = np.float32([[0, 0], [gw, 0], [gw, gh], [0, gh]])
        dst_pts = np.float32([dst_top_left, dst_top_right, dst_bottom_right, dst_bottom_left])

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_garm = cv2.warpPerspective(crop_garm, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        warped_mask = cv2.warpPerspective(crop_mask, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

        # Chekka qirralarni yumshatish (Feathering)
        feathered_mask = cv2.GaussianBlur(warped_mask, (7, 7), 0) / 255.0
        mask_3d = np.repeat(feathered_mask[:, :, np.newaxis], 3, axis=2)

        # 5. Fotometrik Yorug'lik va Soyalarni Ko'chirish (Photometric Relighting)
        gray_user = cv2.cvtColor(person, cv2.COLOR_BGR2GRAY)
        blur_lighting = cv2.bilateralFilter(gray_user, 9, 75, 75)
        ambient_light = np.clip(blur_lighting.astype(float) / 125.0, 0.70, 1.30)

        # Mato burmalari (Folds & Wrinkles)
        folds = self.generate_fabric_folds(H, W, fit_mode, shoulder_dist)
        combined_shading = np.repeat((ambient_light * folds)[:, :, np.newaxis], 3, axis=2)

        shaded_garm = np.clip(warped_garm.astype(float) * combined_shading, 0, 255).astype(np.uint8)

        # 6. Yuz va Bo'yinni Himoyalash (Head & Neck Protection)
        head_mask = np.zeros((H, W), dtype=np.float32)
        neck_radius = int(shoulder_dist * 0.32)
        cv2.circle(head_mask, (int(nose[0]), int(nose[1])), neck_radius, 1.0, -1)
        head_mask = cv2.GaussianBlur(head_mask, (19, 19), 0)
        
        # Yakuniy kiyim maskasi
        final_garment_mask = np.clip(mask_3d * (1.0 - head_mask[:, :, np.newaxis]), 0.0, 1.0)

        # 7. Silliq uyg'unlashtirish (Seamless Alpha Composite)
        result = (person.astype(float) * (1.0 - final_garment_mask) + shaded_garm.astype(float) * final_garment_mask).astype(np.uint8)

        cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 94])
        return output_path

tryon_engine = TryOnEngine()
