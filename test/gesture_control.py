# test/gesture_control.py
import math
import time
import FreeCAD
import FreeCADGui
from commands import CommandProcessor
import mediapipe as mp
from PySide2.QtCore import Qt
from PySide2.QtGui import QPainter, QColor, QPen
from PySide2.QtWidgets import QWidget, QLabel

class GestureCameraController:
    def __init__(self):
        self.fist_start_position = None
        self.circle_radius = 100  # Radius for the control circle
        self.is_controlling = False
        self.last_update = time.time()
        self.update_interval = 1/20  # 20 FPS

    def handle_hand_position(self, landmarks, frame_shape):
        """Handle hand position and gestures for camera control."""
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return None

        self.last_update = current_time

        # Get palm center
        palm_center = self._calculate_palm_center(landmarks)

        # Check if fist is made
        is_fist = self._detect_fist(landmarks)

        # Check if point is made
        is_pointing = self._detect_pointing(landmarks)

        if is_fist and not self.is_controlling:
            # Start of control - record position
            self.fist_start_position = palm_center
            self.is_controlling = True
            return {
                'type': 'control_start',
                'position': palm_center
            }
        elif is_fist and self.is_controlling:
            # Continue control - calculate relative position
            dx, dy = self._calculate_movement_from_palm(palm_center)
            roll = dx / self.circle_radius * 2.0
            pitch = -dy / self.circle_radius * 2.0
            yaw = 0  # Placeholder
            if self.fist_start_position:
                return {
                    'type': 'camera_rotate',
                    'yaw': yaw,
                    'pitch': pitch,
                    'roll': 0,  # Could be calculated from hand rotation if needed
                    'position': palm_center
                }
        elif not is_fist and self.is_controlling:
            # End of control
            self.is_controlling = False
            self.fist_start_position = None
            return {
                'type': 'control_end'
            }
        elif is_pointing and not self.is_controlling:
            # Start point mode
            self.is_controlling = True
            return {
                'type': 'point_start',
                'position': palm_center
            }
        elif is_pointing and self.is_controlling:
            # Perform rotation based on pointing direction
            yaw, pitch, roll = self._calculate_pointing_rotation(landmarks)
            return {
                'type': 'object_rotate',
                'yaw': yaw,
                'pitch': pitch,
                'roll': roll,
            }

        return None

    def _calculate_palm_center(self, landmarks):
        """Calculate the center of the palm using specific landmarks."""
        palm_landmarks = [0, 1, 5, 9, 13, 17]  # Wrist and finger bases
        x_sum = sum(landmarks[i].x for i in palm_landmarks)
        y_sum = sum(landmarks[i].y for i in palm_landmarks)
        return (x_sum / len(palm_landmarks), y_sum / len(palm_landmarks))

    def _calculate_movement_from_palm(self, palm_center):
        """Calculate movement relative to the control start position."""
        dx = palm_center[0] - self.fist_start_position[0]
        dy = palm_center[1] - self.fist_start_position[1]

        # Calculate normalized position within control circle
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > self.circle_radius:
            dx = dx * self.circle_radius / distance
            dy = dy * self.circle_radius / distance

        return dx, dy

    def _detect_fist(self, landmarks):
        """Enhanced fist detection using relative finger positions."""
        finger_tips = [8, 12, 16, 20]  # Index, middle, ring, pinky tips
        finger_bases = [5, 9, 13, 17]  # Corresponding bases

        # Count curled fingers
        curled_count = 0
        for tip, base in zip(finger_tips, finger_bases):
            if landmarks[tip].y > landmarks[base].y:
                curled_count += 1

        # Check thumb separately
        if landmarks[4].x > landmarks[3].x:  # Thumb tip is closer than IP joint
            curled_count += 1

        return curled_count >= 4

    def _calculate_pointing_rotation(self, landmarks):
        """Calculate yaw, pitch, and roll based on pointing direction."""
        index_tip = landmarks[8]
        index_base = landmarks[5]

        # Calculate direction vector
        dx = index_tip.x - index_base.x
        dy = index_tip.y - index_base.y

        # Scale and invert axes as needed
        yaw = dx * 2.0  # Adjust scaling for sensitivity
        pitch = -dy * 2.0  # Adjust scaling and invert if necessary
        roll = 0  # Roll can remain 0 or be mapped to another gesture

        return yaw, pitch, roll

    def _detect_pointing(self, landmarks):
        """Detect if the hand is pointing (index finger extended, others curled)."""
        index_tip = landmarks[8]
        index_base = landmarks[5]

        # Check if index finger is extended
        index_extended = index_tip.y < landmarks[6].y  # Tip above PIP joint

        # Check if other fingers are curled
        other_fingers_curled = (
                landmarks[12].y > landmarks[10].y and  # Middle finger
                landmarks[16].y > landmarks[14].y and  # Ring finger
                landmarks[20].y > landmarks[18].y  # Pinky finger
        )

        return index_extended and other_fingers_curled


class GestureHandler:
    def __init__(self, gesture_controller, object_manager, camera_controller):
        self.mode = "move" # Default mode
        self.is_object_selected = False
        self.gesture_controller = gesture_controller
        self.object_manager = object_manager
        self.camera_controller = camera_controller
        self.is_rotate_mode = False

    def process_gesture(self, gesture_data):
        """Process the detected gesture and perform actions."""
        if gesture_data['type'] == 'point_start':
            self.is_rotate_mode = True
            print("Rotate mode activated.")

        elif gesture_data['type'] == 'object_rotate' and self.is_rotate_mode:
            yaw = gesture_data.get('yaw', 0)
            pitch = gesture_data.get('pitch', 0)
            roll = gesture_data.get('roll', 0)
            print(f"Object rotation data - Yaw: {yaw}, Pitch: {pitch}, Roll: {roll}")
            self.object_manager.rotate_selected_object(yaw, pitch, roll)

        elif gesture_data['type'] == 'control_start':
            print("Move mode activated.")

        elif gesture_data['type'] == 'object_move':
            dx = gesture_data.get('dx', 0)
            dy = gesture_data.get('dy', 0)
            self.object_manager.move_selected_object(dx, dy)

        elif gesture_data['type'] == 'control_end':
            self.is_rotate_mode = False
            print("Control ended.")

    def handle_object_translation(self, gesture_data):
        """Translate the selected object."""
        dx, dy = gesture_data.get('dx', 0), gesture_data.get('dy', 0)
        selected_object = FreeCADGui.Selection.getSelection()[0]
        selected_object.Placement.Base.x += dx
        selected_object.Placement.Base.y += dy
        FreeCADGui.updateGui()

    def rotate_selected_object(self, yaw, pitch, roll):
        """Rotate the selected object."""
        try:
            selected_object = FreeCADGui.Selection.getSelection()[0]
            # Create a FreeCAD rotation
            rotation = FreeCAD.Rotation(roll, pitch, yaw)
            selected_object.Placement.Rotation = selected_object.Placement.Rotation.multiply(rotation)
            FreeCADGui.updateGui()
            print(f"Rotated {selected_object.Name} by (Yaw: {yaw}, Pitch: {pitch}, Roll: {roll})")
        except Exception as e:
            print(f"Error rotating object: {e}")

    def handle_camera_control(self, gesture_data):
        """Control the camera with gestures."""
        yaw = gesture_data.get('yaw', 0)
        pitch = gesture_data.get('pitch', 0)
        # Use existing methods for camera rotation
        rotate_camera(yaw, pitch)

    def _rotate_camera(self, yaw, pitch, roll):
        """Enhanced camera rotation with smooth transitions."""
        try:
            view = FreeCADGui.ActiveDocument.ActiveView

            # Scale factors for smoother rotation
            yaw_scale = 5.0
            pitch_scale = 5.0

            if abs(yaw) > 0.01:
                rotation_angle = yaw * yaw_scale
                view.viewRotateLeft(rotation_angle if yaw > 0 else -rotation_angle)

            if abs(pitch) > 0.01:
                current_dir = view.getViewDirection()
                new_dir = FreeCAD.Vector(
                    current_dir.x,
                    current_dir.y + pitch * pitch_scale,
                    current_dir.z
                )
                view.setViewDirection(new_dir)

            view.redraw()

        except Exception as e:
            print(f"Camera rotation error: {e}")

class GestureVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.fist_position = None
        self.circle_radius = 100
        self.is_controlling = False

    def paintEvent(self, event):
        if not self.is_controlling or not self.fist_position:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw control circle
        pen = QPen(QColor(0, 255, 0, 128))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(
            self.fist_position[0] - self.circle_radius,
            self.fist_position[1] - self.circle_radius,
            self.circle_radius * 2,
            self.circle_radius * 2
        )

        # Draw crosshair at center
        painter.drawLine(
            self.fist_position[0] - 10, self.fist_position[1],
            self.fist_position[0] + 10, self.fist_position[1]
        )
        painter.drawLine(
            self.fist_position[0], self.fist_position[1] - 10,
            self.fist_position[0], self.fist_position[1] + 10
        )

    def update_control_state(self, is_controlling, position=None):
        self.is_controlling = is_controlling
        if position:
            self.fist_position = position
        self.update()

class EnhancedServerConnect:
    def __init__(self, process_data_callback, doc):
        self.doc = doc
        self.gesture_controller = GestureCameraController()
        self.command_processor = CommandProcessor(doc)
        self.gesture_visualizer = GestureVisualizer(FreeCADGui.getMainWindow())
        self.setup_server()

    def setup_server(self):
        """Initialize server for receiving tracking data."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind(('localhost', 12340))
            self.server.listen(1)
        except Exception as e:
            print(f"Server setup error: {e}")

    def process_server_data(self, data):
        """Enhanced data processing with gesture recognition."""
        try:
            if data.startswith("GESTURE:"):
                # Process gesture data
                gesture_parts = data[8:].strip().split(",")
                if len(gesture_parts) >= 4 and gesture_parts[0] == "CAMERA":
                    yaw, pitch, roll = map(float, gesture_parts[1:4])
                    self._rotate_camera(yaw, pitch, roll)
                    # Update visualizer if position data is available
                    if len(gesture_parts) >= 6:
                        x, y = map(float, gesture_parts[4:6])
                        self.gesture_visualizer.update_control_state(True, (x, y))
            elif data.startswith("CREATE:"):
                # Handle object creation
                cmd = data[7:].strip()
                result = self.command_processor.process(cmd)
                print(f"Command result: {result}")
            elif data.startswith("CONTROL_END"):
                self.gesture_visualizer.update_control_state(False)
            elif data.startswith("POINT_DIR:"):
                print(f"Received POINT_DIR data: {data}")
                try:
                    # Extract the part after "POINT_DIR:" (remove the prefix)
                    values = data[len("POINT_DIR:"):].strip()  # Remove the "POINT_DIR:" part

                    # Split the remaining string by commas
                    direction_values = values.split(",")
                    print(f"Direction values after split: {direction_values}")

                    # Ensure there are exactly 3 values (x, y, z)
                    if len(direction_values) != 3:
                        raise ValueError(f"Expected 3 values, got {len(direction_values)}")

                    # Convert to floats and extract coordinates
                    direction_x = float(direction_values[0])
                    direction_y = float(direction_values[1])
                    direction_z = float(direction_values[2])

                    # Print the parsed coordinates for debugging
                    print(f"Received pointing direction: x={direction_x}, y={direction_y}, z={direction_z}")

                    # Add your logic to handle the pointing direction here, e.g., rotate an object.
                    self.rotate_selected_object(direction_x, direction_y, direction_z)

                except ValueError as e:
                    print(f"Error processing direction data: {e}")
                    return

            else:
                # Handle regular finger tracking
                finger_data_list = data.split(";")
                for finger_data in finger_data_list:
                    if not finger_data:
                        continue
                    parts = finger_data.split(",")
                    if len(parts) == 3:
                        finger_id, x, y = map(float, parts)
                        # Update any finger position visualization here

        except Exception as e:
            print(f"Error processing data: {e}")

    def start_server_in_thread(self):
        """Start server in background thread."""
        import threading
        server_thread = threading.Thread(target=self.start_server, daemon=True)
        server_thread.start()

    def start_server(self):
        """Run the server loop."""
        print("Server starting...")
        while True:
            try:
                client, addr = self.server.accept()
                print(f"Connected: {addr}")
                self.handle_client(client)
            except Exception as e:
                print(f"Server error: {e}")
            finally:
                if 'client' in locals():
                    client.close()

    def handle_client(self, client_socket):
        buffer = ""
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    self.process_server_data(message)
            except Exception as e:
                print(f"Client handling error: {e}")
                break