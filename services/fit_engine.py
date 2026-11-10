import cv2
import numpy as np
import os

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except Exception as e:
    HAS_MEDIAPIPE = False
    print(f"FitEngine MediaPipe yuklanmadi: {e}")

class FitEngine:
    def __init__(self):
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "models", "pose_landmarker_lite.task"
        )
        self.detector = None
        if HAS_MEDIAPIPE and os.path.exists(self.model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=False)
                self.detector = vision.PoseLandmarker.create_from_options(options)
            except Exception as e:
                print(f"FitEngine MediaPipe xatoligi: {e}")

        # Local XML fallback
        cascade_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        face_path = os.path.join(cascade_dir, 'haarcascade_frontalface_default.xml')
        self.face_cascade = cv2.CascadeClassifier(face_path) if os.path.exists(face_path) else None

    def analyze_person(self, image_path: str, selected_size: str = "M") -> dict:
        """
        MediaPipe Pose yordamida foydalanuvchining tana nuqtalarini aniq o'lchaydi
        va tanlangan o'lchamga mosligini tahlil qiladi.
        """
        img = cv2.imread(image_path)
        if img is None:
            return {
                "fit_status": "perfect",
                "match_percentage": 90.0,
                "recommended_size": selected_size,
                "fit_advice": "Standart nisbatlar bo'yicha hisoblandi.",
                "body_metrics": {"shoulder_ratio": 0.35}
            }

        H, W = img.shape[:2]
        shoulder_ratio = None
        ratio_shoulder_hip = 1.25

        # 1. MediaPipe orqali aniq 3D koordinatalar
        if self.detector:
            try:
                mp_img = mp.Image.create_from_file(image_path)
                res = self.detector.detect(mp_img)
                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    lm = res.pose_landmarks[0]
                    ls = np.array([lm[11].x * W, lm[11].y * H])
                    rs = np.array([lm[12].x * W, lm[12].y * H])
                    lh = np.array([lm[23].x * W, lm[23].y * H])
                    rh = np.array([lm[24].x * W, lm[24].y * H])

                    shoulder_w = np.linalg.norm(ls - rs)
                    hip_w = np.linalg.norm(lh - rh)

                    shoulder_ratio = shoulder_w / W
                    if hip_w > 10:
                        ratio_shoulder_hip = shoulder_w / hip_w
            except Exception as e:
                print(f"FitEngine pose tahlili xatosi: {e}")

        # Fallback (agar pose topilmasa)
        if shoulder_ratio is None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if self.face_cascade:
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                if len(faces) > 0:
                    fx, fy, fw, fh = faces[0]
                    shoulder_ratio = (fw * 2.8) / W
            if shoulder_ratio is None:
                shoulder_ratio = 0.32

        # 2. O'lcham ranklarini hisoblash
        size_ranks = {"XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6}

        # Tabiiy tana kengligiga qarab tavsiya
        if shoulder_ratio < 0.28:
            recommended = "S"
            ideal_rank = 2
        elif shoulder_ratio > 0.42:
            recommended = "XL"
            ideal_rank = 5
        elif shoulder_ratio > 0.36:
            recommended = "L"
            ideal_rank = 4
        else:
            recommended = "M"
            ideal_rank = 3

        chosen_rank = size_ranks.get(selected_size.upper(), 3)
        diff = chosen_rank - ideal_rank

        if diff == 0:
            fit_status = "perfect"
            match_percentage = 96.5
            fit_advice = (
                f"Tanlangan '{selected_size}' o'lchami qomatingizga ideal o'tiradi. "
                f"Yelka choklari qomatingiz bilan to'liq uyg'unlashib, tabiiy siluet hosil qiladi."
            )
        elif diff < 0:
            fit_status = "tight"
            match_percentage = max(45.0, 88.0 - abs(diff) * 20.0)
            fit_advice = (
                f"Tanlangan '{selected_size}' o'lchami sizga tor (Tight) keladi. "
                f"Yelka va ko'krak qismida mato tarang tortilib, harakatda siqilish his qilinadi. "
                f"Sizga tavsiya etilgan qulay o'lcham: '{recommended}'."
            )
        else:
            fit_status = "loose"
            match_percentage = max(52.0, 89.0 - abs(diff) * 15.0)
            fit_advice = (
                f"Tanlangan '{selected_size}' o'lchami tanangizda erkin va katta (Oversized) turadi. "
                f"Yelka choki pastga tushib, etak qismi keng osilib turadi. "
                f"Klassik aniq o'tirishini istasangiz '{recommended}' o'lchamni tanlang."
            )

        return {
            "fit_status": fit_status,
            "match_percentage": round(float(match_percentage), 1),
            "recommended_size": recommended,
            "fit_advice": fit_advice,
            "body_metrics": {
                "shoulder_ratio": round(float(shoulder_ratio), 3),
                "shoulder_hip_ratio": round(float(ratio_shoulder_hip), 2),
                "chest_estimate_cm": round(88.0 + (ideal_rank - 1) * 6.0, 1),
            }
        }

fit_engine = FitEngine()
