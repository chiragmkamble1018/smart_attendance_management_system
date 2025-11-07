# liveness.py
import cv2
import mediapipe as mp
import numpy as np
import time

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Eye aspect ratio (EAR) for blink detection
def eye_aspect_ratio(eye):
    A = ((eye[1].x - eye[5].x)**2 + (eye[1].y - eye[5].y)**2)**0.5
    B = ((eye[2].x - eye[4].x)**2 + (eye[2].y - eye[4].y)**2)**0.5
    C = ((eye[0].x - eye[3].x)**2 + (eye[0].y - eye[3].y)**2)**0.5
    return (A + B) / (2.0 * C)

def detect_screen_artifacts(frame):
    """
    Conceptual Heuristic for Presentation Attack Detection (PAD).
    Checks for strong, sharp, small reflections/glare common on screen playback.
    (NOTE: This is a weak, heuristic check. True PAD requires a CNN model.)
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Simple thresholding to find extremely bright spots (potential screen glare)
    # Checks for pixels close to white (245 out of 255)
    _, bright_mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
    
    # Find contours of bright spots
    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Count small to medium-sized sharp bright spots (glare from a screen is often sharp/defined)
    unnatural_glare_count = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if 50 < area < 500: # Adjust these values based on camera/lighting
            unnatural_glare_count += 1
    
    # If too many distinct small glare spots are detected, suspect spoofing
    if unnatural_glare_count > 3:
        return True
        
    return False

def detect_blink(frame):
    """Returns status: 'SPOOF_ATTACK', 'BLINK_DETECTED', 'NO_BLINK', or 'NO_FACE'."""
    # Check for screen artifacts first
    if detect_screen_artifacts(frame):
        return "SPOOF_ATTACK"

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        landmarks = face.landmark
        
        # Left eye: [33, 160, 158, 133, 153, 144]
        left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
        ear = eye_aspect_ratio(left_eye)
        
        # Return status string based on EAR
        return "BLINK_DETECTED" if ear < 0.25 else "NO_BLINK"
        
    return "NO_FACE"