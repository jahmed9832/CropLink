import io
import urllib.request
from PIL import Image

def run_test():
    # 1. Create a test RGB image (e.g. Tomato)
    img = Image.new("RGB", (300, 300), (210, 45, 35))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    boundary = "----TestBoundary123"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="camera_photo.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:8000/grade",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )

    with urllib.request.urlopen(req) as resp:
        import json
        data = json.loads(resp.read().decode("utf-8"))
        print("STATUS:", resp.status)
        print("GRADE:", data.get("grade"))
        print("CONFIDENCE:", data.get("confidence"))
        print("PROBABILITIES:", data.get("probabilities"))
        print("VISIBLE_DEFECT_PCT:", data.get("visible_defect_pct"))

if __name__ == "__main__":
    run_test()

