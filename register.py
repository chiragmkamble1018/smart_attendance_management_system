# register.py
import cv2
import face_recognition
import pickle
import sqlite3
import os
import time
from liveness import detect_blink # Now returns a status string

DB_PATH = "attendance.db"
EMBEDDINGS_DIR = "embeddings/"
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        embedding_path TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified TEXT
    )''')
    conn.commit()
    conn.close()

def register_face(name):
    init_db()
    video = cv2.VideoCapture(0)
    if not video.isOpened():
        return False, "❌ Camera not accessible."

    blink_count = 0
    start_time = time.time()
    verified_frame = None
    print(f"Registering {name}: Please blink twice...")

    while time.time() - start_time < 15:  # 15 seconds to blink
        ret, frame = video.read()
        if not ret:
            break

        liveness_status = detect_blink(frame) # Get status

        # --- SPOOF CHECK: Exit immediately on attack ---
        if liveness_status == "SPOOF_ATTACK":
            video.release()
            cv2.destroyAllWindows()
            return False, "❌ **SPOOF DETECTED!** Input rejected. Cannot register from a phone/screen."
        # -----------------------------------------------

        if liveness_status == "BLINK_DETECTED":
            blink_count += 1
            time.sleep(0.4)

        if blink_count >= 2:
            verified_frame = frame.copy()
            break

        cv2.putText(frame, f"Registering {name} - Blinks: {blink_count}/2", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.imshow("Registration - Blink Twice", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()

    if verified_frame is None:
        return False, "❌ Liveness not verified. Registration failed."

    # Process face and save embedding (rest of the logic remains)
    rgb = cv2.cvtColor(verified_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb)
    if len(face_locations) != 1:
        return False, "⚠️ Exactly one face required during registration."

    encodings = face_recognition.face_encodings(rgb, face_locations)
    if not encodings:
        return False, "❌ Could not generate face encoding."

    embedding = encodings[0]
    emb_path = os.path.join(EMBEDDINGS_DIR, f"{name}.pkl")
    with open(emb_path, 'wb') as f:
        pickle.dump(embedding, f)

    # Save to DB
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (name, embedding_path) VALUES (?, ?)", (name, emb_path))
        conn.commit()
        conn.close()
        return True, f"✅ {name} registered successfully!"
    except sqlite3.IntegrityError:
        return False, "❌ Name already exists!"