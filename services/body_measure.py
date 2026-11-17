import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class BodyMeasurer:
    def __init__(self):
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "pose_landmarker_lite.task"
        )
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        if os.path.exists(self.model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
            except Exception as e:
                print(f"[BodyMeasurer] MediaPipe yuklashda xatolik: {e}")
                self.detector = None

    def measure(self, image_data, height_cm: float, weight_kg: float, gender: str = "male") -> dict:
        """
        MediaPipe Pose yordamida tana nuqtalarini topadi va tana parametrlarini hisoblaydi.
        image_data: bytes yoki numpy BGR array.
        Rasm serverda saqlanmaydi (in-memory ishlanadi).
        """
        # 1. Rasmni o'qish (in-memory)
        if isinstance(image_data, bytes):
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_data, np.ndarray):
            img = image_data
        else:
            raise ValueError("Noto'g'ri rasm formati")

        if img is None or img.size == 0:
            raise ValueError("Rasmni o'qib bo'lmadi")

        H, W = img.shape[:2]

        if not self.detector:
            self._init_detector()
            if not self.detector:
                raise RuntimeError("MediaPipe modeli yuklanmagan")

        # 2. MediaPipe Pose orqali tana nuqtalarini aniqlash
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        detection_result = self.detector.detect(mp_img)

        if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
            raise ValueError("Butun bo'y ko'rinadigan, oldindan olingan rasm yuklang")

        landmarks = detection_result.pose_landmarks[0]
        if len(landmarks) < 33:
            raise ValueError("Butun bo'y ko'rinadigan, oldindan olingan rasm yuklang")

        # 3. To'liq bo'y ko'rinishini tekshirish
        # Asosiy nuqtalar indekslari:
        # 0: burun
        # 11, 12: yelkalar (chap, o'ng)
        # 23, 24: son/bel bo'g'imlari (chap, o'ng)
        # 25, 26: tizzalar (chap, o'ng)
        # 27, 28: to'piqlar (chap, o'ng)
        # 29, 30: tovonlar
        # 31, 32: oyoq uchlari
        nose = landmarks[0]
        ls, rs = landmarks[11], landmarks[12]
        lh, rh = landmarks[23], landmarks[24]
        lk, rk = landmarks[25], landmarks[26]
        la, ra = landmarks[27], landmarks[28]

        # Qomat to'liq kadr ichida ekanligini tekshirish
        # Yelkalar, sonlar, tizzalar va to'piqlar ko'rinishi shart
        key_points = [ls, rs, lh, rh, lk, rk, la, ra]
        visibilities = [getattr(p, 'visibility', 1.0) for p in key_points]
        avg_vis = float(np.mean(visibilities)) if visibilities else 1.0

        # Agar yelkalar, sonlar yoki oyoqlar kadr tashqarisida yoki ko'rinmas bo'lsa
        feet_y = max([la.y, ra.y, landmarks[29].y, landmarks[30].y, landmarks[31].y, landmarks[32].y])
        head_y = min([nose.y, landmarks[1].y, landmarks[4].y, landmarks[7].y, landmarks[8].y])

        # Bosh qismi va to'piqlar yetarli darajada kadrda bo'lishi kerak
        if feet_y < 0.60 or head_y > 0.40 or (la.y > 1.15 and ra.y > 1.15):
            raise ValueError("Butun bo'y ko'rinadigan, oldindan olingan rasm yuklang")

        # 4. Bo'y piksellarini aniqlash va masshtab (cm_per_pixel)
        # Bosh tepasini burun va yelka masofasidan taxmin qilish
        shoulder_mid_y = (ls.y + rs.y) / 2.0
        head_top_est_y = max(0.0, nose.y - abs(shoulder_mid_y - nose.y) * 0.85)
        pixel_height = (feet_y - head_top_est_y) * H

        if pixel_height < H * 0.45 or pixel_height <= 20:
            raise ValueError("Butun bo'y ko'rinadigan, oldindan olingan rasm yuklang")

        cm_per_pixel = float(height_cm) / float(pixel_height)

        # 5. Tana o'lchamlarini hisoblash
        # A) Yelka kengligi (sm)
        ls_px = np.array([ls.x * W, ls.y * H])
        rs_px = np.array([rs.x * W, rs.y * H])
        shoulder_width_px = float(np.linalg.norm(ls_px - rs_px))
        shoulder_raw_cm = shoulder_width_px * cm_per_pixel
        # Anatomik chegaralarda silliqlash
        shoulder_cm = round(float(np.clip(shoulder_raw_cm, 34.0, 56.0)), 1)

        # B) Son suyagi (hip) oraliq kengligi
        lh_px = np.array([lh.x * W, lh.y * H])
        rh_px = np.array([rh.x * W, rh.y * H])
        hip_width_px = float(np.linalg.norm(lh_px - rh_px))
        hip_bone_cm = hip_width_px * cm_per_pixel

        # C) Jins va BMI asosida aylanalar (ko'krak, bel, bo'ksa)
        h_m = max(1.0, float(height_cm) / 100.0)
        bmi = float(weight_kg) / (h_m ** 2)
        bmi = float(np.clip(bmi, 15.0, 42.0))
        bmi_delta = bmi - 22.0

        is_female = (str(gender).lower() == "female")

        if is_female:
            # Ayollar uchun
            chest_circ = shoulder_cm * 2.18 + bmi_delta * 1.35
            waist_circ = shoulder_cm * 1.68 + bmi_delta * 1.55
            hip_circ = max(waist_circ * 1.30, hip_bone_cm * 3.4 + bmi_delta * 1.25)
        else:
            # Erkaklar uchun
            chest_circ = shoulder_cm * 2.22 + bmi_delta * 1.45
            waist_circ = shoulder_cm * 1.84 + bmi_delta * 1.65
            hip_circ = max(waist_circ * 1.14, hip_bone_cm * 3.2 + bmi_delta * 1.15)

        # Anatomik me'yorlar bilan cheklash
        chest_cm = round(float(np.clip(chest_circ, 72.0, 145.0)), 1)
        waist_cm = round(float(np.clip(waist_circ, 58.0, 140.0)), 1)
        hip_cm = round(float(np.clip(hip_circ, 78.0, 145.0)), 1)

        confidence = round(float(np.clip(avg_vis if avg_vis > 0 else 0.88, 0.50, 0.99)), 2)

        # 6. Normallashtirilgan koordinatalar (0-1)
        normalized_landmarks = [
            {
                "x": round(float(lm.x), 4),
                "y": round(float(lm.y), 4),
                "z": round(float(lm.z), 4),
                "visibility": round(float(getattr(lm, "visibility", 1.0)), 3)
            }
            for lm in landmarks
        ]

        return {
            "shoulder_cm": shoulder_cm,
            "chest_cm": chest_cm,
            "waist_cm": waist_cm,
            "hip_cm": hip_cm,
            "confidence": confidence,
            "landmarks": normalized_landmarks
        }

# Global singleton
body_measurer = BodyMeasurer()
