import math
import socket


class FingerTrackingServer:
    def __init__(self, host='localhost', port=12345):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(1)
        self.running = True
        self.buffer = ""

        # Map finger IDs to names for readable output
        self.finger_names = {
            0: "thumb",
            1: "index",
            2: "middle",
            3: "ring",
            4: "pinky"
        }

    def start(self):
        print(f"Server started, waiting for connections...")
        try:
            client_socket, address = self.server.accept()
            print(f"Client connected from {address}")
            self.handle_client(client_socket)
        except Exception as e:
            print(f"Error accepting connection: {e}")
        finally:
            self.cleanup()

    def handle_client(self, client_socket):
        while self.running:
            try:
                # Receive data
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                self.buffer += data

                # Process complete messages (split by newlines)
                while '\n' in self.buffer:
                    # Get the first complete message
                    message, self.buffer = self.buffer.split('\n', 1)

                    # Process the coordinate string
                    self.process_coordinates(message)

            except socket.error as e:
                print(f"Socket error: {e}")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

    def process_coordinates(self, coord_string):
        """Process incoming coordinate strings."""
        if not coord_string:
            return

        print("\nProcessing message:", coord_string)

        # Check for POINT_DIR command
        if coord_string.startswith("POINT_DIR:"):
            try:
                # Extract the part after "POINT_DIR:" (remove the prefix)
                values = coord_string[len("POINT_DIR:"):].strip()  # Remove the "POINT_DIR:" part

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

                # Add your logic to handle the pointing direction here, e.g., rotate an object.
                # rotate_selected_object(direction_x, direction_y, direction_z)

            except ValueError as e:
                print(f"Error processing direction data: {e}")
                return

        else:
            # Handle finger position data
            print("\nVisible fingers:")
            # Split based on semicolon
            finger_coords = coord_string.split(';')

            for coord in finger_coords:
                if coord:
                    try:
                        # Parse finger ID and coordinates
                        finger_id, x, y = map(int, coord.split(','))
                        finger_name = self.finger_names.get(finger_id, f"finger{finger_id}")
                        print(f"{finger_name}: x={x}, y={y}")

                        # Example logic for finger positions
                        if finger_id == 1:  # Index
                            self.index_pos = (x, y)
                        elif finger_id == 0:  # Thumb
                            self.thumb_pos = (x, y)

                    except ValueError as e:
                        print(f"Error parsing coordinates: {e}")

    def cleanup(self):
        self.running = False
        self.server.close()
        print("Server shutdown complete")

def calculate_distance(point1, point2):
    return math.sqrt((point1["x"] - point2.x) ** 2 + (point1["y"] - point2.y) ** 2)


if __name__ == "__main__":
    server = FingerTrackingServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.cleanup()