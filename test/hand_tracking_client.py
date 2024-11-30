import socket
import cv2
import mediapipe as mp
import time
import sys
import numpy as np
import math

# Initialize MediaPipe hands with optimization flagss
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,  # Only track one hand for better performance
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

class HandGestureDetector:
    def __init__(self):
        self.is_fist = False
        self.is_pinch = False
        self.is_pointing = False
        self.last_palm_position = None
        self.initial_fist_position = None
        self.palm_landmarks = [0, 1, 5, 9, 13, 17]
        self.THRESHOLD_X = 0.1
        self.THRESHOLD_Y_UP = 0.1
        self.THRESHOLD_Y_DOWN = 0.25
        self.last_timestamp = None
        self.last_direction = None
        self.last_sent_time = time.time()
        self.MIN_SEND_INTERVAL = 0.05
        self.frame_count = 0
        self.PINCH_THRESHOLD = 0.05  # Adjust this value based on testing
        self.start_time = time.time()


    def can_send_update(self):
        current_time = time.time()
        if current_time - self.last_sent_time >= self.MIN_SEND_INTERVAL:
            self.last_sent_time = current_time
            return True
        return False

    def detect_pinch(self, hand_landmarks):
        """Detect pinch gesture between thumb and index finger"""
        thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

        # Calculate distance between thumb and index finger
        distance = ((thumb_tip.x - index_tip.x) ** 2 +
                   (thumb_tip.y - index_tip.y) ** 2 +
                   (thumb_tip.z - index_tip.z) ** 2) ** 0.5

        # Calculate pinch point (midway between thumb and index)
        pinch_point = {
            'x': (thumb_tip.x + index_tip.x) / 2,
            'y': (thumb_tip.y + index_tip.y) / 2,
            'z': (thumb_tip.z + index_tip.z) / 2
        }

        # Check if fingers are close enough to be considered pinching
        is_pinching = distance < self.PINCH_THRESHOLD

        return is_pinching, pinch_point if is_pinching else None

    def detect_fist(self, hand_landmarks):
        # Optimized fist detection with less computation
        finger_tips = [
            (mp_hands.HandLandmark.THUMB_TIP, mp_hands.HandLandmark.THUMB_IP),
            (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
            (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
            (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
            (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP)
        ]

        curled_fingers = sum(1 for tip, pip in finger_tips
                           if hand_landmarks.landmark[tip].y > hand_landmarks.landmark[pip].y)
        return curled_fingers >= 4

    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points in 3D space."""
        return math.sqrt(
            (point1.x - point2.x) ** 2 +
            (point1.y - point2.y) ** 2 +
            (point1.z - point2.z) ** 2
        )

    def detect_pointing(self, hand_landmarks):
        """Detect pointing gesture with index finger extended and other fingers curled."""
        # Get landmarks for the index and other fingers
        index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]

        middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]

        ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
        ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]

        pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
        pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]

        # Thresholds
        extended_distance_threshold = 0.1  # Minimum distance to consider finger extended
        curled_distance_threshold = 0.12  # Maximum distance to consider finger curled

        # Check if index finger is extended
        index_distance = self.calculate_distance(index_tip, index_pip)
        index_extended = index_distance > extended_distance_threshold

        # Check if other fingers are curled
        middle_distance = self.calculate_distance(middle_tip, middle_pip)
        ring_distance = self.calculate_distance(ring_tip, ring_pip)
        pinky_distance = self.calculate_distance(pinky_tip, pinky_pip)

        other_fingers_curled = (
                middle_distance < curled_distance_threshold and
                ring_distance < curled_distance_threshold and
                pinky_distance < curled_distance_threshold
        )

        # Debugging information
        print(f"Index Distance: {index_distance}, Index Extended: {index_extended}")
        print(f"Middle Distance: {middle_distance}, Ring Distance: {ring_distance}, Pinky Distance: {pinky_distance}")
        print(f"Other Fingers Curled: {other_fingers_curled}")

        # Check pointing condition
        is_pointing = index_extended and other_fingers_curled

        if is_pointing:
            # Calculate normalized pointing vector
            pointing_vector = {
                'x': index_tip.x - index_pip.x,
                'y': index_tip.y - index_pip.y,
                'z': index_tip.z - index_pip.z
            }
            vector_magnitude = math.sqrt(
                pointing_vector['x'] ** 2 +
                pointing_vector['y'] ** 2 +
                pointing_vector['z'] ** 2
            )

            if vector_magnitude > 0:
                pointing_vector = {k: v / vector_magnitude for k, v in pointing_vector.items()}
            else:
                pointing_vector = {'x': 0, 'y': 0, 'z': 0}

            return True, pointing_vector

        return False, None

    def get_movement_direction(self, dx, dy):
        """Determine movement direction based on displacement"""
        if abs(dx) < self.THRESHOLD_X and abs(dy) < self.THRESHOLD_Y_UP:
            return "CENTER"

        # Determine primary direction
        if abs(dx) > abs(dy):  # Horizontal movement is stronger
            if dx > self.THRESHOLD_X/5:
                return "RIGHT"
            elif dx < -self.THRESHOLD_X:
                return "LEFT"
        else:  # Vertical movement is stronger
            if dy < -self.THRESHOLD_Y_UP:  # Moving up
                return "UP"
            elif dy > self.THRESHOLD_Y_DOWN/5:  # Moving down - using different threshold
                return "DOWN"

        return "CENTER"

    def calculate_palm_orientation(self, hand_landmarks, timestamp):
        if not self.is_fist:
            self.initial_fist_position = None
            self.last_direction = None
            return None, None, None

        palm_points = [hand_landmarks.landmark[i] for i in self.palm_landmarks]
        palm_center = np.mean([[p.x, p.y, p.z] for p in palm_points], axis=0)

        if self.initial_fist_position is None:
            self.initial_fist_position = palm_center
            print("Initial fist position recorded:", palm_center)
            return 0, 0, 0

        # Calculate movement vector components
        dx = palm_center[0] - self.initial_fist_position[0]
        dy = palm_center[1] - self.initial_fist_position[1]

        # Scale the movements (adjust these multipliers as needed)
        movement_scale = 5  # Adjust this to control movement sensitivity
        scaled_dx = dx * movement_scale
        scaled_dy = dy * movement_scale

        print(f"Movement vector: dx={scaled_dx:.2f}, dy={scaled_dy:.2f}")

        # Return the scaled movement vector
        return scaled_dx, scaled_dy, "VECTOR"

    def calculate_fps(self):
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 1.0:  # Update FPS every second
            fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.start_time = time.time()
            return f"FPS: {fps:.1f}"
        return None

class HandTrackingClient:
    def __init__(self):
        self.client = None
        self.cap = None
        self.gesture_detector = HandGestureDetector()
        self.running = True

    def setup_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")

    def setup_connection(self, server_address):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not connect_with_retry(self.client, server_address):
            raise RuntimeError("Failed to connect to server")

    def process_frame(self, frame):
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        point_status = "NOT POINTING"   # Default pinch status

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Send finger coordinates
                coord_str = format_coordinates(hand_landmarks, frame.shape)
                print(f"Sending finger coords: {coord_str}")
                self.client.send(coord_str.encode('utf-8'))

                # Check for fist gesture and handle movement
                self.gesture_detector.is_fist = self.gesture_detector.detect_fist(hand_landmarks)

                # Check for pointing gesture
                self.gesture_detector.is_pointing = self.gesture_detector.detect_pointing(hand_landmarks)

                # Check for pinch gesture
                is_pinching, pinch_point = self.gesture_detector.detect_pinch(hand_landmarks)
                if is_pinching and pinch_point:
                    # Convert normalized coordinates to screen coordinates
                    screen_x = int(pinch_point['x'] * frame.shape[1])
                    screen_y = int(pinch_point['y'] * frame.shape[0])
                    pinch_cmd = f"PINCH:{screen_x},{screen_y}\n"
                    self.client.send(pinch_cmd.encode('utf-8'))

                    # Draw pinch point
                    cv2.circle(frame, (screen_x, screen_y), 5, (0, 255, 0), -1)

                # Check for pointing gesture
                is_pointing, pointing_vector = self.gesture_detector.detect_pointing(hand_landmarks)
                if is_pointing and pointing_vector:
                    # Convert normalized direction vector to a readable format
                    direction_x = int(pointing_vector['x'] * 100)  # Scale for demonstration
                    direction_y = int(pointing_vector['y'] * 100)
                    direction_z = int(pointing_vector['z'] * 100)

                    point_cmd = f"POINT_DIR:{direction_x},{direction_y},{direction_z}\n"
                    print(f"Sending POINT_DIR command: {point_cmd}")
                    self.client.send(point_cmd.encode('utf-8'))

                    # Visualize the pointing vector on the frame (projected direction)
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    start_point = (int(index_tip.x * frame.shape[1]), int(index_tip.y * frame.shape[0]))
                    end_point = (start_point[0] + direction_x, start_point[1] + direction_y)

                    # Draw pointing direction on the frame
                    cv2.arrowedLine(frame, start_point, end_point, (255, 0, 0), 2)
                    cv2.circle(frame, start_point, 5, (0, 255, 0), -1)

                if self.gesture_detector.is_fist and self.gesture_detector.can_send_update():
                    dx, dy, _ = self.gesture_detector.calculate_palm_orientation(
                        hand_landmarks, time.time())
                    if dx is not None:
                        movement_cmd = f"VECTOR:{dx:.2f},{dy:.2f}\n"
                        self.client.send(movement_cmd.encode('utf-8'))

        # Add gesture status to frame
        status = "FIST" if self.gesture_detector.is_fist else "TRACKING"
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return frame

    def run(self):
        try:
            self.setup_camera()
            self.setup_connection(('localhost', 12340))

            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break

                processed_frame = self.process_frame(frame)
                cv2.imshow("Hand Tracking", processed_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        print("\nCleaning up resources...")
        if self.cap is not None:
            self.cap.release()
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.client.close()
        cv2.destroyAllWindows()
        print("Cleanup complete")

def connect_with_retry(client, server_address, max_attempts=5):
    """Attempt to connect to server with retries."""
    for attempt in range(max_attempts):
        try:
            print(f"Attempting to connect to server (attempt {attempt + 1}/{max_attempts})...")
            client.connect(server_address)
            print("Connected successfully!")
            return True
        except ConnectionRefusedError:
            if attempt < max_attempts - 1:
                print("Connection refused. Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("Could not connect to server after maximum attempts")
                return False
        except Exception as e:
            print(f"Unexpected error while connecting: {e}")
            return False
    return False

def format_coordinates(hand_landmarks, frame_shape):
    """Matrix format: finger_id,x,y;finger_id,x,y;..."""
    fingers = [
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]

    finger_coords = []
    for finger_id, landmark_id in enumerate(fingers):
        landmark = hand_landmarks.landmark[landmark_id]
        x = int(landmark.x * frame_shape[1])
        y = int(landmark.y * frame_shape[0])
        if 0 <= x < frame_shape[1] and 0 <= y < frame_shape[0]:
            finger_coords.append(f"{finger_id},{x},{y}")

    return ";".join(finger_coords) + "\n"

if __name__ == "__main__":
    client = HandTrackingClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nStopping hand tracking...")
    finally:
        client.cleanup()