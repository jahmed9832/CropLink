"""Photo grading (A/B/C). Image -> color/defect features -> RandomForest. Confidence soho."""
import io
import json
import os
import base64
from typing import Optional

import joblib
import numpy as np
import PIL
import sklearn
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFile
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

# Safe limits for image uploads
ImageFile.LOAD_TRUNCATED_IMAGES = False
Image.MAX_IMAGE_PIXELS = 10_000_000  # Safe cap (10 MP) to prevent decompression bombs

from ..config import settings
from ..i18n import t

GRADES = ["A", "B", "C"]
LOW_CONFIDENCE = 0.60


class ImageDecodeError(ValueError):
    """Raised when image bytes cannot be decoded."""
    pass


def safe_open_image(data: bytes, return_issues: bool = False):
    """Safely open any image format (JPEG, PNG, WEBP, BMP, AVIF, TIFF) and convert to RGB.
    Note: HEIC is unsupported unless external codec library is installed.
    """
    if not data or len(data) == 0:
        raise ImageDecodeError("Empty image payload")

    raw = data
    issues = []

    # Check if data-URL base64
    if b";base64," in data[:128]:
        try:
            raw = base64.b64decode(data.split(b";base64,", 1)[1], validate=True)
        except Exception as e:
            raise ImageDecodeError(f"Invalid data-URL base64: {e}") from e
    else:
        # Check if raw data starts with non-image ASCII base64 characters
        # Try raw first; if that fails, try strict base64 decode with validate=True
        try:
            bio = io.BytesIO(raw)
            Image.open(bio)
        except Exception:
            try:
                raw = base64.b64decode(raw, validate=True)
            except Exception as e:
                raise ImageDecodeError(f"Cannot decode image data: {e}") from e

    try:
        bio = io.BytesIO(raw)
        img = Image.open(bio)
        img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ImageDecodeError("Image exceeds maximum pixel dimensions (decompression bomb)") from e
    except (OSError, IOError) as e:
        if "truncated" in str(e).lower():
            # Turn on truncated images only for this fallback read
            try:
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                bio.seek(0)
                img = Image.open(bio)
                img.load()
                issues.append("truncated_image")
            except Exception as e2:
                raise ImageDecodeError(f"Cannot decode truncated image: {e2}") from e2
            finally:
                ImageFile.LOAD_TRUNCATED_IMAGES = False
        else:
            raise ImageDecodeError(f"Cannot read image: {e}") from e
    except Exception as e:
        raise ImageDecodeError(f"Cannot read image: {e}") from e

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode != "RGB":
        try:
            img = img.convert("RGB")
        except Exception as e:
            raise ImageDecodeError(f"Cannot convert image to RGB: {e}") from e

    # Downscale very large photos to keep processing fast (<0.05s)
    if img.width > 1200 or img.height > 1200:
        img.thumbnail((1200, 1200))

    if return_issues:
        return img, issues
    return img


def image_features(img: Image.Image):
    img = img.convert("RGB").resize((96, 96))
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    fg = (s > 0.20) | (v < 0.40)  # background = light/gray
    n = max(1, int(fg.sum()))
    frac_fg = n / fg.size
    hf, sf, vf = h[fg], s[fg], v[fg]
    if hf.size == 0:
        hf, sf, vf = h.ravel(), s.ravel(), v.ravel()
    dark = float(((vf < 0.30)).mean())
    brown = float(((hf > 0.04) & (hf < 0.11) & (vf < 0.50) & (sf > 0.3)).mean())
    green = float(((hf > 0.18) & (hf < 0.45)).mean())
    red = float(((hf < 0.04) | (hf > 0.93)).mean())
    yellow = float(((hf >= 0.08) & (hf <= 0.18)).mean())
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    gy, gx = np.gradient(gray)
    edge = float(np.sqrt(gx ** 2 + gy ** 2)[fg].mean()) if fg.any() else 0.0
    return [frac_fg, float(hf.mean()), float(sf.mean()), float(vf.mean()), float(sf.std()), float(vf.std()),
            dark, brown, green, red, yellow, edge]


def compute_defect_pct(img: Image.Image) -> float:
    img = img.convert("RGB").resize((96, 96))
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    fg = (s > 0.20) | (v < 0.40)
    if not fg.any():
        hf, sf, vf = h.ravel(), s.ravel(), v.ravel()
    else:
        hf, sf, vf = h[fg], s[fg], v[fg]
    # Single combined boolean mask so pixels aren't counted twice
    defect_mask = (vf < 0.30) | ((hf > 0.04) & (hf < 0.11) & (vf < 0.50) & (sf > 0.3))
    pct = float(defect_mask.mean()) * 100.0
    return max(0.0, min(100.0, round(pct, 1)))


PALETTES = [(205, 40, 35), (150, 40, 60), (60, 140, 50), (190, 150, 90), (215, 130, 40), (110, 170, 70), (120, 60, 140)]


def synth_image(grade, rng):
    base = np.array(PALETTES[rng.integers(len(PALETTES))], dtype=float)
    if grade == "C":
        base = base * rng.uniform(0.6, 0.85) + rng.normal(0, 14, 3)
    elif grade == "B":
        base = base * rng.uniform(0.8, 0.98) + rng.normal(0, 8, 3)
    else:
        base = base * rng.uniform(0.95, 1.08)
    bg = int(rng.integers(225, 252))
    img = Image.new("RGB", (96, 96), (bg, bg, bg - int(rng.integers(0, 10))))
    d = ImageDraw.Draw(img)
    cx, cy = 48 + rng.integers(-5, 6), 48 + rng.integers(-5, 6)
    rx, ry = rng.integers(26, 38), rng.integers(24, 36)
    col = tuple(int(np.clip(x, 0, 255)) for x in base)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col)
    nspots = {"A": rng.integers(0, 2), "B": rng.integers(2, 5), "C": rng.integers(4, 10)}[grade]
    rmax = {"A": 2, "B": 5, "C": 9}[grade]
    for _ in range(int(nspots)):
        r = int(rng.integers(1, rmax + 1))
        ang, dist = rng.uniform(0, 6.28), rng.uniform(0, 0.8)
        x = cx + int(np.cos(ang) * rx * dist)
        y = cy + int(np.sin(ang) * ry * dist)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(int(rng.integers(40, 90)), int(rng.integers(25, 55)), 20))
    img = img.filter(ImageFilter.GaussianBlur(float(rng.uniform(0, 0.8))))
    arr = np.asarray(img, dtype=float) + rng.normal(0, 4, (96, 96, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))


def load_real_dataset(root):
    """data/images/<A|B|C>/*.jpg thakle seta use hobe (real training)."""
    X, y = [], []
    for g in GRADES:
        folder = os.path.join(root, g)
        if not os.path.isdir(folder):
            continue
        for fn in os.listdir(folder):
            try:
                X.append(image_features(Image.open(os.path.join(folder, fn))))
                y.append(g)
            except Exception:
                pass
    return X, y


def train(n_per_class=1000, seed=11):
    real_X, real_y = load_real_dataset(os.path.join(settings.DATA_DIR, "images"))
    source = "synthetic"
    if len(real_y) >= 150:
        X, y, source = real_X, real_y, "real_images"
    else:
        rng = np.random.default_rng(seed)
        X, y = [], []
        for g in GRADES:
            for _ in range(n_per_class):
                X.append(image_features(synth_image(g, rng)))
                y.append(g)
    X, y = np.array(X), np.array(y)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
    clf = RandomForestClassifier(n_estimators=250, min_samples_leaf=3, random_state=0)
    clf.fit(Xtr, ytr)
    p = clf.predict(Xte)
    metrics = {
        "data_source": source,
        "accuracy": round(float(accuracy_score(yte, p)), 3),
        "macro_f1": round(float(f1_score(yte, p, average="macro")), 3),
        "n_test": int(len(yte)),
        "warning": "Metrics are on synthetic data. Real accuracy cannot be claimed until retrained on real Bangladesh crop photos."
        if source == "synthetic" else None,
        "versions": {
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
            "pillow": PIL.__version__
        }
    }
    clf.fit(X, y)
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    joblib.dump(clf, os.path.join(settings.MODELS_DIR, "grader.joblib"))
    with open(os.path.join(settings.MODELS_DIR, "grader_metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)
    return metrics


class Grader:
    def __init__(self):
        model_path = os.path.join(settings.MODELS_DIR, "grader.joblib")
        metrics_path = os.path.join(settings.MODELS_DIR, "grader_metrics.json")
        if not os.path.exists(model_path) or not os.path.exists(metrics_path):
            raise FileNotFoundError("Grader model or metrics file not found")
        self.clf = joblib.load(model_path)
        with open(metrics_path) as fh:
            self.metrics = json.load(fh)

        saved_sklearn = self.metrics.get("versions", {}).get("scikit-learn")
        if saved_sklearn and saved_sklearn != sklearn.__version__:
            raise RuntimeError(f"Grader scikit-learn version mismatch: model was trained on {saved_sklearn}, current is {sklearn.__version__}")

    def grade_bytes(self, data: bytes, crop: Optional[str] = "tomato"):
        img, issues = safe_open_image(data, return_issues=True)
        f = np.array([image_features(img)])
        proba = self.clf.predict_proba(f)[0]
        idx = int(np.argmax(proba))
        feats = f[0]
        conf = float(proba[idx])
        if feats[0] < 0.12:
            issues.append(t("grade.small"))
        if feats[3] < 0.2:
            issues.append(t("grade.dark"))
        needs_review = conf < LOW_CONFIDENCE or bool(issues)
        defect_pct = compute_defect_pct(img)
        return {
            "crop": crop or "tomato",
            "grade": self.clf.classes_[idx],
            "confidence": round(conf, 3),
            "probabilities": {c: round(float(p), 3) for c, p in zip(self.clf.classes_, proba)},
            "visible_defect_pct": defect_pct,
            "needs_manual_review": needs_review,
            "image_issues": issues,
            "model_note": t("grade.note"),
            "model_data_source": self.metrics.get("data_source", "synthetic")
        }
