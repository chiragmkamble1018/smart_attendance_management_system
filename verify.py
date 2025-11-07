# verify.py
import cv2
import face_recognition
import pickle
import sqlite3
import time
import os
from liveness import detect_blink # Now returns a status string

def init_db():
    conn = sqlite3.connect("attendance.db")
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

def verify_attendance():
    init_db()  # Ensure tables exist

    video = cv2.VideoCapture(0)
    if not video.isOpened():
        print("❌ Cannot access camera.")
        return

    blink_count = 0
    start_time = time.time()
    verified_live = False
    verified_frame = None
    spoof_detected = False

    print("👀 Please blink twice to prove you're real...")

    while time.time() - start_time < 10:  # 10-second window
        ret, frame = video.read()
        if not ret:
            print("❌ Failed to read frame.")
            break

        liveness_status = detect_blink(frame) # Get status
        
        # --- SPOOF CHECK: Exit immediately on attack ---
        if liveness_status == "SPOOF_ATTACK":
            spoof_detected = True
            break
        # -----------------------------------------------

        # Detect blink
        if liveness_status == "BLINK_DETECTED":
            blink_count += 1
            print(f"Blinks detected: {blink_count}")
            time.sleep(0.4)  # Debounce

        # If liveness confirmed, save this frame and break
        if blink_count >= 2:
            verified_live = True
            verified_frame = frame.copy()
            print("✅ Liveness verified!")
            break

        # Display blink count
        cv2.putText(frame, f"Blinks: {blink_count}/2", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Liveness Check - Blink Twice", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()

    # Log spoof attempt and exit
    if spoof_detected:
        print("🚨 **SPOOF DETECTED!** Input rejected. Cannot mark attendance from a phone/screen.")
        # Optional: Log the spoof attempt to the database (user_id=None, verified="Spoof Detected")
        return

    # If liveness failed
    if not verified_live:
        print("❌ Liveness check failed (no two blinks). Attendance denied.")
        return

    # --- Recognition Logic (rest of the logic remains) ---
    rgb_frame = cv2.cvtColor(verified_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)

    if len(face_locations) != 1:
        print("⚠️ Exactly one face must be visible for recognition.")
        return

    face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]

    # Load registered users and compare
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    c.execute("SELECT id, name, embedding_path FROM users")
    users = c.fetchall()
    conn.close()

    matched_user = None
    for user_id, name, emb_path in users:
        if not os.path.exists(emb_path):
            print(f"⚠️ Embedding file missing for {name}: {emb_path}")
            continue
        with open(emb_path, 'rb') as f:
            stored_encoding = pickle.load(f)
        distance = face_recognition.face_distance([stored_encoding], face_encoding)[0]
        if distance < 0.6:
            matched_user = (user_id, name)
            break

    # Log attendance
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    if matched_user:
        user_id, name = matched_user
        c.execute("INSERT INTO attendance (user_id, verified) VALUES (?, ?)",
                  (user_id, "Live Verified"))
        conn.commit()
        print(f"✅ Attendance marked for {name}!")
    else:
        c.execute("INSERT INTO attendance (user_id, verified) VALUES (?, ?)",
                  (None, "Live but Unrecognized"))
        conn.commit()
        print("❌ Face not recognized. Liveness passed, but no match in database.")

    conn.close()