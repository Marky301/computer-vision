# test_commands.py
import time
from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QLabel, QWidget
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtGui import QPainter, QColor, QPen


import math
from setup import setup_freecad_env
setup_freecad_env()

import socket
import threading
import FreeCAD
import FreeCADGui
from commands import CommandProcessor

class HandTrackingOverlay(QWidget):
    def __init__(self, parent=None):
        # Get FreeCAD main window
        self.main_window = FreeCADGui.getMainWindow()
        super().__init__(self.main_window)
        
        # Set window flags for overlay
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Match size to FreeCAD window
        self.setGeometry(self.main_window.geometry())
        
        self.finger_positions = {}
        
        # Semi-transparent background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 10);")
        
        # Timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(16)  # 60fps
        self.highlight_pos = None

        self.selected_object = None
        self.highlight_timer = QTimer()
        self.highlight_timer.timeout.connect(self.clear_highlight)
        self.highlight_timer.setSingleShot(True)
        
        
        # Create labels for finger positions
        self.finger_labels = {}
        for i in range(5):
            label = QLabel(self.main_window)
            label.setStyleSheet(
                "QLabel { background-color: black; color: white; padding: 5px; border-radius: 5px; }"
            )
            label.setGeometry(10, 10 + i*40, 300, 30)
            label.show()
            self.finger_labels[i] = label
        
        # Create label for selected object
        self.selection_label = QLabel(self)
        self.selection_label.setStyleSheet(
            "QLabel { background-color: rgba(0, 0, 0, 180); color: yellow; padding: 5px; border-radius: 5px; }"
        )
        self.selection_label.setGeometry(10, 250, 300, 30)
        self.selection_label.hide()
        
        self.show()

    def highlight_selection(self, x, y):
        """Temporarily highlight the selection point"""
        self.highlight_pos = (x, y)
        self.update()
        # Clear highlight after 500ms
        self.highlight_timer.start(500)
        
    def clear_highlight(self):
        """Clear the highlight"""
        self.highlight_pos = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw finger positions
        for finger_id, pos in self.finger_positions.items():
            colors = {
                0: QColor(255, 0, 0),    # Red for thumb
                1: QColor(0, 255, 0),    # Green for index
                2: QColor(0, 0, 255),    # Blue for middle
                3: QColor(255, 255, 0),  # Yellow for ring
                4: QColor(255, 0, 255)   # Magenta for pinky
            }
            
            pen = QPen(colors.get(finger_id, QColor(255, 255, 255)))
            pen.setWidth(3)
            painter.setPen(pen)
            
            x, y = pos
            painter.drawEllipse(int(x)-5, int(y)-5, 10, 10)
            painter.drawText(int(x)+10, int(y)+10, f"F{finger_id}")
          
            if self.highlight_pos:
                x, y = self.highlight_pos
                painter.setPen(QPen(QColor(255, 255, 0)))  # Yellow
                painter.setBrush(QColor(255, 255, 0, 100))  # Semi-transparent yellow
                painter.drawEllipse(int(x)-15, int(y)-15, 30, 30)
                
    def update_finger_position(self, finger_id, x, y):
        self.finger_positions[finger_id] = (x, y)
        # Update label text
        if finger_id in self.finger_labels:
            self.finger_labels[finger_id].setText(f"Finger {finger_id}: x={x:.1f}, y={y:.1f}")
        self.update()

    def moveEvent(self, event):
        """Keep overlay aligned with FreeCAD window"""
        if self.main_window:
            self.setGeometry(self.main_window.geometry())


    def set_selected_object(self, object_name):
        """Update the selected object display"""
        self.selected_object = object_name
        self.selection_label.setText(f"Selected: {object_name}")
        self.selection_label.show()
        self.update()
    
    def clear_selection(self):
        """Clear the selection display"""
        self.selected_object = None
        self.selection_label.hide()
        self.highlight_pos = None
        self.update()


class ObjectRotator:
    def __init__(self):
        self.previous_yaw = 0.0
        self.previous_pitch = 0.0
        self.previous_roll = 0.0
        self.smoothing_factor = 0.005    # Lower to slow down rotation
        self.rotation_speed = 0.5
        self.continue_rotation = False  # Flag to control rotation state
        self.last_update_time = time.time()

    def rotate_selected_object(self, target_x, target_y, target_z):
        """Smoothly rotate the object towards the target direction."""
        if self.continue_rotation:
            # Calculate the difference between the current and target rotation values
            diff_x = target_x - self.previous_yaw
            diff_y = target_y - self.previous_pitch
            diff_z = target_z - self.previous_roll

            # Apply smoothing factor
            smoothed_x = self.previous_yaw + diff_x * self.smoothing_factor
            smoothed_y = self.previous_pitch + diff_y * self.smoothing_factor
            smoothed_z = self.previous_roll + diff_z * self.smoothing_factor

            # Apply rotation speed factor
            smoothed_x *= self.rotation_speed
            smoothed_y *= self.rotation_speed
            smoothed_z *= self.rotation_speed

            # Update previous rotation values
            self.previous_yaw = smoothed_x
            self.previous_pitch = smoothed_y
            self.previous_roll = smoothed_z

            # Apply the smoothed rotation to the object
            print(f"Rotating object smoothly: yaw={smoothed_x}, pitch={smoothed_y}, roll={smoothed_z}")
            self.apply_rotation_to_object(smoothed_x, smoothed_y, smoothed_z)

    def apply_rotation_to_object(self, yaw, pitch, roll):
        """Apply the calculated rotation to the selected object in FreeCAD."""
        if FreeCADGui.Selection.getSelection():
            obj = FreeCADGui.Selection.getSelection()[0]
            try:
                # Create a new placement or transformation matrix
                obj.Placement = obj.Placement.multiply(
                    FreeCAD.Placement(
                        FreeCAD.Vector(0, 0, 0),  # No translation
                        FreeCAD.Rotation(yaw, pitch, roll)  # Apply rotation
                    )
                )
            except Exception as e:
                print(f"Error applying rotation: {e}")
        else:
            print("No object selected!")

    def stop_rotation(self):
        """Stop rotating the object."""
        self.continue_rotation = False
        print("Rotation stopped.")

    def start_rotation(self, target_x, target_y, target_z):
        """Start continuous rotation in the pointing direction."""
        self.continue_rotation = True
        self.rotate_selected_object(target_x, target_y, target_z)
        self.last_update_time = time.time()

    def check_pointing_direction(self, direction_x, direction_y, direction_z):
        """Called periodically to check if the pointing direction is the same for a certain duration."""
        current_time = time.time()
        # If no pointing direction is received for 0.5 seconds, stop rotation
        if current_time - self.last_update_time > 0.5:  # Adjust duration as needed
            self.stop_rotation()
        else:
            self.start_rotation(direction_x, direction_y, direction_z)

    def process_pointing_direction(self, direction_x, direction_y, direction_z):
        """Process the pointing direction and start rotation."""
        if FreeCADGui.Selection.getSelection():
            obj = FreeCADGui.Selection.getSelection()[0]
        else:
            print("No object selected!")
            return

        # Start rotation if pointing direction changes
        self.start_rotation(direction_x, direction_y, direction_z)

        # Call the update function periodically to rotate the object
        self.update_rotation()

    def update_rotation(self):
        """Continuously rotate the object as long as pointing direction is being received."""
        if self.continue_rotation:
            # Perform rotation update every frame or periodically
            self.rotate_selected_object(self.previous_yaw, self.previous_pitch, self.previous_roll)


object_rotator = ObjectRotator()


class ServerConnect(QtCore.QObject):
    def __init__(self, process_data_callback, doc):
        super().__init__()
        self.doc = doc
        self.overlay = HandTrackingOverlay()
        self.command_processor = CommandProcessor(doc)
        # Create a default object
        self.create_default_object()
        self.setup_server()
        self.movement_step = 5  # How many units to move per command
        self.last_pinch_time = 0
        self.PINCH_COOLDOWN = 0.5  # Minimum time between pinches in seconds
        
        self.view_widget = self.find_3d_view()

        self.is_rotating = False
        self.last_direction = None

    def find_3d_view(self):
        """Find the 3D view widget in FreeCAD's main window"""
        try:
            mw = FreeCADGui.getMainWindow()
            # The 3D view is in the central widget of the main window
            central = mw.centralWidget()
            # Print information about the central widget
            print(f"Central widget: {central.objectName()}")
            
            # Find all OpenGL widgets (the 3D view uses OpenGL)
            for widget in central.findChildren(QtWidgets.QWidget):
                if isinstance(widget, QtWidgets.QOpenGLWidget) or "view" in widget.objectName().lower():
                    print(f"Found potential view widget: {widget.objectName()}")
                    return widget
                    
            # Alternative: try to find the MDI area which contains the 3D view
            mdi_area = mw.findChild(QtWidgets.QMdiArea)
            if mdi_area:
                print("Found MDI area")
                # Get the active subwindow
                active_window = mdi_area.activeSubWindow()
                if active_window:
                    print(f"Active window: {active_window.objectName()}")
                    return active_window.widget()
                    
            print("Could not find 3D view widget")
            return None
            
        except Exception as e:
            print(f"Error finding 3D view: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def move_object(self, direction):
        """Move the default cube based on direction"""
        try:
            if not hasattr(self, 'cube'):
                print("No cube to move!")
                return

            # Get current position
            current_pos = self.cube.Placement.Base
            
            # Calculate new position based on direction
            if direction == "LEFT":
                new_pos = FreeCAD.Vector(current_pos.x - self.movement_step, current_pos.y, current_pos.z)
            elif direction == "RIGHT":
                new_pos = FreeCAD.Vector(current_pos.x + self.movement_step, current_pos.y, current_pos.z)
            elif direction == "UP":
                new_pos = FreeCAD.Vector(current_pos.x, current_pos.y, current_pos.z + self.movement_step)
            elif direction == "DOWN":
                new_pos = FreeCAD.Vector(current_pos.x, current_pos.y, current_pos.z - self.movement_step)
            else:
                return

            # Update position
            self.cube.Placement.Base = new_pos
            self.doc.recompute()
            
            # Print for debugging
            print(f"Moved {direction}: New position = ({new_pos.x}, {new_pos.y}, {new_pos.z})")
            
        except Exception as e:
            print(f"Error moving object: {e}")

    def extrude_selected_object(self, direction, amount=0.5):
        """Extrude or intrude the selected object based on direction and selected face."""
        try:
            # Get selection
            selection = FreeCADGui.Selection.getSelectionEx()
            if not selection:
                print("No object selected!")
                return

            obj = selection[0].Object
            subname = selection[0].SubElementNames[0] if selection[0].SubElementNames else None

            if not subname or not subname.startswith('Face'):
                print("Please select a face to extrude!")
                return

            # Get the face number (indexed from 1)
            face_index = int(subname[4:]) - 1

            # Create unit-aware quantities
            current_length = FreeCAD.Units.Quantity(obj.Length)
            current_width = FreeCAD.Units.Quantity(obj.Width)
            current_height = FreeCAD.Units.Quantity(obj.Height)
            delta = FreeCAD.Units.Quantity(str(amount) + " mm")

            # Get current placement
            pos = obj.Placement.Base
            current_x = FreeCAD.Units.Quantity(str(pos.x) + " mm")
            current_y = FreeCAD.Units.Quantity(str(pos.y) + " mm")
            current_z = FreeCAD.Units.Quantity(str(pos.z) + " mm")

            # Map face indices to dimensions with proper unit handling
            if face_index == 0:  # Back face
                if direction == "LEFT":
                    obj.Placement.Base = FreeCAD.Vector(pos.x, (current_y - delta).Value, pos.z)
                    obj.Length = current_length + delta
                else:
                    if current_length.Value > 1.0:
                        obj.Length = current_length - delta
            elif face_index == 1:  # Front face
                if direction == "LEFT":
                    obj.Length = current_length + delta
                else:
                    if current_length.Value > 1.0:
                        obj.Placement.Base = FreeCAD.Vector(pos.x, (current_y + delta).Value, pos.z)
                        obj.Length = current_length - delta
            elif face_index == 2:  # Right face
                if direction == "LEFT":
                    obj.Width = current_width + delta
                else:
                    if current_width.Value > 1.0:
                        obj.Width = current_width - delta
            elif face_index == 3:  # Left face
                if direction == "LEFT":
                    obj.Placement.Base = FreeCAD.Vector((current_x - delta).Value, pos.y, pos.z)
                    obj.Width = current_width + delta
                else:
                    if current_width.Value > 1.0:
                        obj.Width = current_width - delta
            elif face_index == 4:  # Top face
                if direction == "LEFT":
                    obj.Height = current_height + delta
                else:
                    if current_height.Value > 1.0:
                        obj.Height = current_height - delta
            elif face_index == 5:  # Bottom face
                if direction == "LEFT":
                    obj.Placement.Base = FreeCAD.Vector(pos.x, pos.y, (current_z - delta).Value)
                    obj.Height = current_height + delta
                else:
                    if current_height.Value > 1.0:
                        obj.Height = current_height - delta

            # Update the view
            self.doc.recompute()
            print(f"{'Extruded' if direction == 'LEFT' else 'Intruded'} {subname} by {amount} mm")

        except Exception as e:
            print(f"Error during extrusion: {e}")
    def create_default_object(self):
        """Create a default cube in the scene."""
        try:
            # Create a cube
            self.cube = self.doc.addObject("Part::Box", "DefaultCube")
            self.cube.Length = 20
            self.cube.Width = 20
            self.cube.Height = 20

            # Position it at origin
            self.cube.Placement.Base = FreeCAD.Vector(0, 0, 0)

            # Set visual properties
            self.cube.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red color

            self.doc.recompute()

            # Set up the view
            view = FreeCADGui.ActiveDocument.ActiveView
            view.viewAxonometric()

            # Fit view to object
            view.fitAll()

        except Exception as e:
            print(f"Error creating default object: {e}")
            import traceback
            traceback.print_exc()

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

        """Process incoming tracking data."""
        try:
            if data.startswith("PEACE:"):
                direction = data[6:].strip()  # Get LEFT or RIGHT
                print(f"Peace sign movement detected: {direction}")
                self.extrude_selected_object(direction)
            elif data.startswith("VECTOR:"):
                # Handle vector movement
                dx, dy = map(float, data[7:].strip().split(','))
                self.move_object_by_vector(dx, dy)
            elif data.startswith("MOVE:"):
                # Handle movement commands
                direction = data[5:].strip()
                print(f"Received movement command: {direction}")
                self.move_object(direction)
            elif data.startswith("CAMERA:"):
                # Handle camera rotation
                rotations = data[7:].strip().split(",")
                yaw, pitch, roll = map(float, rotations)
                self._rotate_camera(yaw, pitch, roll)
            elif data.startswith("PINCH:"):
                current_time = time.time()
                # Only process pinch if enough time has passed since last pinch
                if current_time - self.last_pinch_time > self.PINCH_COOLDOWN:
                    x, y = map(int, data[6:].strip().split(','))
                    self.select_object_at_point(x, y)
                    self.last_pinch_time = current_time
            elif data.startswith("POINT_DIR:") or data.startswith("POINT:"):
                try:
                    # Extract the pointing direction data
                    if data.startswith("POINT_DIR:"):
                        values = data[len("POINT_DIR:"):].strip()  # Remove the "POINT_DIR:" part
                    elif data.startswith("POINT:"):
                        values = data[len("POINT:"):].strip()  # Remove the "POINT:" part

                    # Split the remaining string by commas
                    direction_values = values.split(",")

                    # Ensure there are exactly 3 values (x, y, z)
                    if len(direction_values) != 3:
                        raise ValueError(f"Expected 3 values, got {len(direction_values)}")

                    # Convert to floats and extract coordinates
                    direction_x = float(direction_values[0])
                    direction_y = float(direction_values[1])
                    direction_z = float(direction_values[2])

                    # Print the parsed coordinates for debugging
                    print(f"Received pointing direction: x={direction_x}, y={direction_y}, z={direction_z}")

                    # If the pointing direction is close to zero or neutral, stop rotation
                    if abs(direction_x) < 5.0 and abs(direction_y) < 5.0 and abs(direction_z) < 5.0:
                        object_rotator.stop_rotation()  # Stop rotation when the pointing direction is near neutral
                        print("Rotation stopped due to neutral pointing direction.")
                    else:
                        # Rotate the selected object based on the pointing direction
                        object_rotator.process_pointing_direction(direction_x, direction_y, direction_z)

                except ValueError as e:
                    print(f"Error processing direction data: {e}")
                    return

            else:
                # Handle normal finger tracking
                finger_data_list = data.split(";")
                for finger_data in finger_data_list:
                    if not finger_data:
                        continue
                    parts = finger_data.split(",")
                    if len(parts) != 3:
                        continue
                    finger_id, x, y = map(float, parts)
                    self.overlay.update_finger_position(int(finger_id), x, y)
        except Exception as e:
            print(f"Error processing data: {e}")

    def clear_selection(self):
        """Clear current selection"""
        FreeCADGui.Selection.clearSelection()
        self.command_processor.selected = None
        self.overlay.clear_selection()
        print("Selection cleared")

    def select_object_at_point(self, screen_x, screen_y):
        """Simulate mouse clicks for selection"""
        try:
            if not self.view_widget:
                print("No 3D view widget found")
                self.view_widget = self.find_3d_view()
                if not self.view_widget:
                    return

            current_time = time.time()
            if current_time - self.last_pinch_time < self.PINCH_COOLDOWN:
                return

            print(f"Simulating click at: {screen_x}, {screen_y}")
            
            # Create mouse press event
            press = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonPress,
                QtCore.QPoint(screen_x, screen_y),
                QtCore.Qt.LeftButton,
                QtCore.Qt.LeftButton,
                QtCore.Qt.NoModifier
            )
            
            # Create mouse release event
            release = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonRelease,
                QtCore.QPoint(screen_x, screen_y),
                QtCore.Qt.LeftButton,
                QtCore.Qt.NoButton,
                QtCore.Qt.NoModifier
            )
            
            # Send events directly to the view widget
            if self.view_widget:
                print(f"Sending events to widget: {self.view_widget.objectName()}")
                QtWidgets.QApplication.postEvent(self.view_widget, press)
                QtWidgets.QApplication.postEvent(self.view_widget, release)
                
                # Delay for a moment
                QtCore.QTimer.singleShot(100, lambda: self.check_selection())
            
            self.last_pinch_time = current_time
            
        except Exception as e:
            print(f"Selection error: {e}")
            import traceback
            traceback.print_exc()

    def check_selection(self):
        """Check what was selected after mouse events"""
        selected = FreeCADGui.Selection.getSelection()
        if selected:
            self.command_processor.selected = selected[0]
            print(f"Selected: {selected[0].Name}")
        else:
            print("No object selected")

    def _rotate_camera(self, yaw, pitch, roll):
        """Rotate camera using FreeCAD's direct view methods."""
        try:
            view = FreeCADGui.ActiveDocument.ActiveView
            
            # Scale the movements (smaller for smoother rotation)
            scale = 0.1
            
            if abs(yaw) > 0.1:
                # Use viewRotateLeft/Right for yaw
                if yaw > 0:
                    view.viewRotateLeft()
                else:
                    view.viewRotateRight()
                    
            if abs(pitch) > 0.1:
                # Use viewTop/Bottom for pitch
                current_dir = view.getViewDirection()
                new_dir = FreeCAD.Vector(current_dir.x, current_dir.y + pitch * scale, current_dir.z)
                view.setViewDirection(new_dir)
                
            view.redraw()
            
        except Exception as e:
            print(f"Error rotating camera: {e}")
            import traceback
            traceback.print_exc()

    def start_server(self):
        """Run the server loop."""
        print("Server starting...")
        while True:
            try:
                client, addr = self.server.accept()
                print(f"Connected: {addr}")
                while True:
                    data = client.recv(1024).decode('utf-8')
                    if not data:
                        break
                    self.process_server_data(data)
            except Exception as e:
                print(f"Server error: {e}")
            finally:
                if 'client' in locals():
                    client.close()

    def run_server_in_thread(self):
        """Start server in background thread."""
        server_thread = threading.Thread(target=self.start_server, daemon=True)
        server_thread.start()
        print("Server thread started")

    def move_object_by_vector(self, dx, dy):
        """Move the selected object based on movement vector"""
        try:
            # First check if there's an object selected through the command processor
            if hasattr(self, 'command_processor') and self.command_processor.selected:
                obj = self.command_processor.selected
            # Otherwise check if there's an active selection in FreeCAD
            elif FreeCADGui.Selection.getSelection():
                obj = FreeCADGui.Selection.getSelection()[0]
            else:
                # Fall back to default cube if it exists
                if hasattr(self, 'cube'):
                    obj = self.cube
                else:
                    print("No object selected to move!")
                    return

            # Get current position
            current_pos = obj.Placement.Base
            
            # Calculate new position (note: adjust mapping of x,y to FreeCAD coordinates)
            new_pos = FreeCAD.Vector(
                current_pos.x + dx,  # x movement
                current_pos.y,       # y stays the same
                current_pos.z - dy   # inverted y for up/down
            )
            
            # Update position
            obj.Placement.Base = new_pos
            self.doc.recompute()
            
            print(f"Moved {obj.Name} to: ({new_pos.x:.2f}, {new_pos.y:.2f}, {new_pos.z:.2f})")
            
        except Exception as e:
            print(f"Error moving object: {e}")
            import traceback
            traceback.print_exc()