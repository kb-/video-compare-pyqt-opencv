import logging  # For logging exceptions
import os  # For file name extraction
import sys

import cv2
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QImage, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

# Configure logging
logging.basicConfig(
    filename="video_compare.log",
    level=logging.ERROR,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


class OverlayVideoLabel(QWidget):
    divisionChanged = pyqtSignal(float)  # Signal to emit when division changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame1 = None
        self.frame2 = None
        self.division = 0.5  # Default division at center
        self.setMinimumSize(400, 225)  # Set a reasonable minimum size

        # Variables to handle dragging
        self.dragging = False
        self.handle_width = 10  # Width of the draggable area around the divider

    def set_frames(self, frame1, frame2):
        self.frame1 = frame1
        self.frame2 = frame2
        print("OverlayVideoLabel: Frames set.")
        self.update()

    def set_division(self, division):
        self.division = division
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.frame1 is None or self.frame2 is None:
            return

        painter = QPainter(self)
        widget_width = self.width()
        widget_height = self.height()

        # Convert frames to QImage and scale them while maintaining aspect ratio
        try:
            rgb_frame1 = cv2.cvtColor(self.frame1, cv2.COLOR_BGR2RGB)
            q_img1 = QImage(
                rgb_frame1.data,
                rgb_frame1.shape[1],
                rgb_frame1.shape[0],
                rgb_frame1.strides[0],
                QImage.Format.Format_RGB888,
            ).scaled(
                widget_width,
                widget_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            rgb_frame2 = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2RGB)
            q_img2 = QImage(
                rgb_frame2.data,
                rgb_frame2.shape[1],
                rgb_frame2.shape[0],
                rgb_frame2.strides[0],
                QImage.Format.Format_RGB888,
            ).scaled(
                widget_width,
                widget_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception as e:
            logging.error(f"Error converting frames: {e}")
            return

        # Calculate positions to center the images
        img1_width = q_img1.width()
        img1_height = q_img1.height()
        img2_width = q_img2.width()
        img2_height = q_img2.height()

        # Center both images
        img1_x = (widget_width - img1_width) // 2
        img1_y = (widget_height - img1_height) // 2

        img2_x = (widget_width - img2_width) // 2
        img2_y = (widget_height - img2_height) // 2

        # Determine the image area based on the smaller width
        image_area_width = min(img1_width, img2_width)
        image_area_x = (widget_width - image_area_width) // 2

        # Calculate the division point within the image area
        division_x = image_area_x + int(self.division * image_area_width)

        # **Implement Clipping for Overlay Mode**

        # 1. Draw the first image (left part) up to division_x
        painter.save()  # Save the current painter state
        painter.setClipRect(0, 0, division_x, widget_height)  # Set clipping region
        painter.drawImage(QPoint(img1_x, img1_y), q_img1)
        painter.restore()  # Restore the painter state

        # 2. Draw the second image (right part) from division_x onwards
        painter.save()
        painter.setClipRect(division_x, 0, widget_width - division_x, widget_height)
        painter.drawImage(QPoint(img2_x, img2_y), q_img2)
        painter.restore()

        # Draw the divider
        painter.setPen(QColor(255, 255, 255))
        painter.drawLine(division_x, 0, division_x, widget_height)

        # Draw a handle for better UX
        handle_width = 5
        handle_color = QColor(255, 255, 255)
        painter.fillRect(
            QRect(division_x - handle_width // 2, 0, handle_width, widget_height),
            handle_color,
        )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            widget_width = self.width()
            widget_height = self.height()

            if self.frame1 is None or self.frame2 is None:
                return

            # Convert frames to QImage and scale them
            try:
                rgb_frame1 = cv2.cvtColor(self.frame1, cv2.COLOR_BGR2RGB)
                q_img1 = QImage(
                    rgb_frame1.data,
                    rgb_frame1.shape[1],
                    rgb_frame1.shape[0],
                    rgb_frame1.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                rgb_frame2 = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2RGB)
                q_img2 = QImage(
                    rgb_frame2.data,
                    rgb_frame2.shape[1],
                    rgb_frame2.shape[0],
                    rgb_frame2.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            except Exception as e:
                logging.error(f"Error during mousePressEvent scaling: {e}")
                return

            # Calculate image area
            img1_width = q_img1.width()
            img2_width = q_img2.width()
            image_area_width = min(img1_width, img2_width)
            image_area_x = (widget_width - image_area_width) // 2

            # Calculate division point
            division_x = image_area_x + int(self.division * image_area_width)

            # Check if click is near the divider
            if abs(event.position().x() - division_x) <= self.handle_width:
                self.dragging = True
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                event.accept()
            else:
                self.dragging = False
                event.ignore()
        else:
            self.dragging = False
            event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            widget_width = self.width()
            widget_height = self.height()

            if self.frame1 is None or self.frame2 is None:
                return

            # Convert frames to QImage and scale them
            try:
                rgb_frame1 = cv2.cvtColor(self.frame1, cv2.COLOR_BGR2RGB)
                q_img1 = QImage(
                    rgb_frame1.data,
                    rgb_frame1.shape[1],
                    rgb_frame1.shape[0],
                    rgb_frame1.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                rgb_frame2 = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2RGB)
                q_img2 = QImage(
                    rgb_frame2.data,
                    rgb_frame2.shape[1],
                    rgb_frame2.shape[0],
                    rgb_frame2.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            except Exception as e:
                logging.error(f"Error during mouseMoveEvent scaling: {e}")
                return

            # Calculate image area
            img1_width = q_img1.width()
            img2_width = q_img2.width()
            image_area_width = min(img1_width, img2_width)
            image_area_x = (widget_width - image_area_width) // 2

            # Calculate new division based on mouse position
            new_division_x = int(event.position().x())

            # Clamp the division within the image area (1% to 99%)
            new_division_x = max(
                int(0.01 * image_area_width) + image_area_x,
                min(new_division_x, int(0.99 * image_area_width) + image_area_x),
            )

            # Update division ratio
            self.division = (new_division_x - image_area_x) / image_area_width
            self.update()

            # Emit the divisionChanged signal
            self.divisionChanged.emit(self.division)
            event.accept()
        else:
            # Change cursor if hovering near the divider
            widget_width = self.width()
            widget_height = self.height()

            if self.frame1 is None or self.frame2 is None:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                return

            # Convert frames to QImage and scale them
            try:
                rgb_frame1 = cv2.cvtColor(self.frame1, cv2.COLOR_BGR2RGB)
                q_img1 = QImage(
                    rgb_frame1.data,
                    rgb_frame1.shape[1],
                    rgb_frame1.shape[0],
                    rgb_frame1.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                rgb_frame2 = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2RGB)
                q_img2 = QImage(
                    rgb_frame2.data,
                    rgb_frame2.shape[1],
                    rgb_frame2.shape[0],
                    rgb_frame2.strides[0],
                    QImage.Format.Format_RGB888,
                ).scaled(
                    widget_width,
                    widget_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            except Exception as e:
                logging.error(f"Error during mouseMoveEvent scaling (hover): {e}")
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                return

            # Calculate image area
            img1_width = q_img1.width()
            img2_width = q_img2.width()
            image_area_width = min(img1_width, img2_width)
            image_area_x = (widget_width - image_area_width) // 2

            # Calculate division point
            division_x = image_area_x + int(self.division * image_area_width)

            # Change cursor if near the divider
            if abs(event.position().x() - division_x) <= self.handle_width:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
        else:
            event.ignore()


class VideoCompareApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Compare")
        self.resize(1200, 700)  # Set a reasonable default size

        # Initialize variables
        self.cap1 = None
        self.cap2 = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.is_paused = False
        self.is_overlay = False  # Flag for overlay mode

        # Setup UI
        self.init_ui()

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Mode Toggle
        self.mode_toggle = QCheckBox("Overlay Mode")
        self.mode_toggle.stateChanged.connect(self.toggle_mode)
        self.mode_toggle.setEnabled(False)  # Disable initially
        self.main_layout.addWidget(self.mode_toggle)

        # Stacked Layout for Video Displays
        self.stacked_layout = QStackedLayout()

        # Side-by-Side Layout
        self.side_by_side_widget = QWidget()
        side_by_side_layout = QHBoxLayout(self.side_by_side_widget)
        side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        side_by_side_layout.setSpacing(10)

        # Video 1 display
        self.video1_layout = QVBoxLayout()
        self.video_label_1 = QLabel("Video 1")
        self.video_label_1.setStyleSheet("background-color: black;")
        self.video_label_1.setScaledContents(False)  # Disable scaled contents
        self.video_label_1.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )  # Center the pixmap
        self.video1_layout.addWidget(self.video_label_1)
        side_by_side_layout.addLayout(self.video1_layout)

        # Video 2 display
        self.video2_layout = QVBoxLayout()
        self.video_label_2 = QLabel("Video 2")
        self.video_label_2.setStyleSheet("background-color: black;")
        self.video_label_2.setScaledContents(False)  # Disable scaled contents
        self.video_label_2.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )  # Center the pixmap
        self.video2_layout.addWidget(self.video_label_2)
        side_by_side_layout.addLayout(self.video2_layout)

        self.stacked_layout.addWidget(self.side_by_side_widget)

        # Overlay Layout
        self.overlay_widget = QWidget()
        overlay_layout = QVBoxLayout(self.overlay_widget)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(10)

        # Overlay Video Display
        self.overlay_label = OverlayVideoLabel()
        self.overlay_label.divisionChanged.connect(self.on_division_changed)
        overlay_layout.addWidget(self.overlay_label)

        self.stacked_layout.addWidget(self.overlay_widget)

        self.main_layout.addLayout(self.stacked_layout)

        # File Names Layout (Placed above Metadata)
        self.filenames_layout = QHBoxLayout()
        self.filename_label_1 = QLabel("Video 1 Filename: N/A")
        self.filename_label_1.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.filename_label_1.setStyleSheet("font-weight: bold;")
        self.filename_label_2 = QLabel("Video 2 Filename: N/A")
        self.filename_label_2.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.filename_label_2.setStyleSheet("font-weight: bold;")
        self.filenames_layout.addWidget(self.filename_label_1)
        self.filenames_layout.addWidget(self.filename_label_2)
        self.main_layout.addLayout(self.filenames_layout)

        # Metadata Info Layout
        self.metadata_layout = QHBoxLayout()

        self.info_label_1 = QLabel("Video 1 Info: N/A")
        self.info_label_2 = QLabel("Video 2 Info: N/A")
        self.info_label_1.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label_2.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.metadata_layout.addWidget(self.info_label_1)
        self.metadata_layout.addWidget(self.info_label_2)

        self.main_layout.addLayout(self.metadata_layout)

        # Controls Layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Load Videos Button
        self.load_button = QPushButton("Load Videos")
        self.load_button.clicked.connect(self.load_videos)
        controls_layout.addWidget(self.load_button)

        # Play Button
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_videos)
        self.play_button.setEnabled(False)
        controls_layout.addWidget(self.play_button)

        # Pause Button
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_videos)
        self.pause_button.setEnabled(False)
        controls_layout.addWidget(self.pause_button)

        # Stop Button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_videos)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)

        # Seekbar
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderMoved.connect(self.seek_videos)
        self.seek_slider.sliderPressed.connect(self.start_seek)
        self.seek_slider.sliderReleased.connect(self.end_seek)
        controls_layout.addWidget(self.seek_slider)

        self.main_layout.addLayout(controls_layout)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     # If videos are loaded and not in overlay mode, rescale the current frames
    #     if self.cap1 and self.cap2 and not self.is_overlay:
    #         # Get the current frame positions
    #         pos1 = self.cap1.get(cv2.CAP_PROP_POS_FRAMES)
    #         pos2 = self.cap2.get(cv2.CAP_PROP_POS_FRAMES)
    #         self.cap1.set(cv2.CAP_PROP_POS_FRAMES, pos1)
    #         self.cap2.set(cv2.CAP_PROP_POS_FRAMES, pos2)
    #         ret1, frame1 = self.cap1.read()
    #         ret2, frame2 = self.cap2.read()
    #         if ret1 and ret2:
    #             self.display_frame(frame1, self.video_label_1)
    #             self.display_frame(frame2, self.video_label_2)
    #         # Reset frame positions
    #         self.cap1.set(cv2.CAP_PROP_POS_FRAMES, pos1)
    #         self.cap2.set(cv2.CAP_PROP_POS_FRAMES, pos2)

    def toggle_mode(self, state):
        if state == Qt.CheckState.Checked.value:
            if not self.cap1 or not self.cap2:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Please load both videos before switching to Overlay Mode.",
                )
                self.mode_toggle.setChecked(False)
                return
            self.is_overlay = True
            self.stacked_layout.setCurrentWidget(self.overlay_widget)
            print("Switched to Overlay Mode")
        else:
            self.is_overlay = False
            self.stacked_layout.setCurrentWidget(self.side_by_side_widget)
            print("Switched to Side-by-Side Mode")
        # Refresh display to update frames
        self.display_initial_frames()

    def load_videos(self):
        # Open file dialog to select first video
        video1_path, _ = QFileDialog.getOpenFileName(
            self, "Select First Video", filter="Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if not video1_path:
            QMessageBox.warning(self, "Warning", "First video not selected.")
            return

        # Open file dialog to select second video
        video2_path, _ = QFileDialog.getOpenFileName(
            self, "Select Second Video", filter="Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if not video2_path:
            QMessageBox.warning(self, "Warning", "Second video not selected.")
            return

        print(f"Video 1: {video1_path}")
        print(f"Video 2: {video2_path}")

        # Release previous captures if any
        if self.cap1:
            self.cap1.release()
        if self.cap2:
            self.cap2.release()

        # Initialize VideoCapture objects
        self.cap1 = cv2.VideoCapture(video1_path)
        self.cap2 = cv2.VideoCapture(video2_path)

        # Check if videos opened successfully
        if not self.cap1.isOpened():
            QMessageBox.critical(
                self,
                "Error",
                "Failed to open the first video. Please check the file and try again.",
            )
            logging.error(f"Failed to open first video: {video1_path}")
            return
        if not self.cap2.isOpened():
            QMessageBox.critical(
                self,
                "Error",
                "Failed to open the second video. Please check the file and try again.",
            )
            logging.error(f"Failed to open second video: {video2_path}")
            return

        # Retrieve video properties
        self.fps1 = self.cap1.get(cv2.CAP_PROP_FPS)
        self.frame_count1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration1 = self.frame_count1 / self.fps1 if self.fps1 else 0

        self.fps2 = self.cap2.get(cv2.CAP_PROP_FPS)
        self.frame_count2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration2 = self.frame_count2 / self.fps2 if self.fps2 else 0

        # Retrieve frame sizes
        width1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
        height1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
        height2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Extract file names
        filename1 = os.path.basename(video1_path)
        filename2 = os.path.basename(video2_path)

        # Update filename labels
        self.filename_label_1.setText(f"Video 1 Filename: {filename1}")
        self.filename_label_2.setText(f"Video 2 Filename: {filename2}")

        # Update metadata info labels
        self.info_label_1.setText(
            f"Video 1 Info: Resolution: {width1}x{height1}, FPS: {self.fps1:.2f}, Duration: {self.duration1:.2f} sec"
        )
        self.info_label_2.setText(
            f"Video 2 Info: Resolution: {width2}x{height2}, FPS: {self.fps2:.2f}, Duration: {self.duration2:.2f} sec"
        )

        # Enable playback controls
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.seek_slider.setEnabled(True)

        # Enable overlay toggle now that videos are loaded
        self.mode_toggle.setEnabled(True)

        # Set seekbar range based on the shorter duration
        self.duration = min(self.duration1, self.duration2)
        self.seek_slider.setRange(0, int(self.duration * 1000))
        self.seek_slider.setValue(0)
        print(f"Seekbar range set to 0 - {int(self.duration)} seconds")

        # Reset video positions to start
        self.cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Display first frames
        self.display_initial_frames()

    def display_initial_frames(self):
        if not self.cap1 or not self.cap2:
            print("Display Initial Frames: Video captures not initialized.")
            return
        ret1, frame1 = self.cap1.read()
        ret2, frame2 = self.cap2.read()

        if ret1 and ret2:
            if self.is_overlay:
                print("Setting frames for overlay mode.")
                self.overlay_label.set_frames(frame1, frame2)
            else:
                print("Setting frames for side-by-side mode.")
                self.display_frame(frame1, self.video_label_1)
                self.display_frame(frame2, self.video_label_2)
        else:
            print("Failed to read frames from one or both videos.")

        # Reset frame positions to start
        self.cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def display_frame(self, frame, label):
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(
                rgb_frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(q_img)
            # Resize pixmap to fit label while keeping aspect ratio
            pixmap = pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label.setPixmap(pixmap)
        except cv2.error as e:
            logging.error(f"OpenCV error during frame display: {e}")
            QMessageBox.critical(
                self, "Error", f"An error occurred while displaying a frame:\n{str(e)}"
            )
        except Exception as e:
            logging.error(f"Unexpected error during frame display: {e}")
            QMessageBox.critical(
                self, "Error", f"An unexpected error occurred:\n{str(e)}"
            )

    def play_videos(self):
        if not self.cap1 or not self.cap2:
            QMessageBox.warning(self, "Warning", "Please load both videos first.")
            return

        # Calculate interval based on FPS
        # Using the higher FPS to ensure smooth playback
        combined_fps = max(self.fps1, self.fps2)
        if combined_fps <= 0:
            QMessageBox.critical(
                self, "Error", "Invalid FPS detected. Cannot start playback."
            )
            logging.error(f"Invalid combined FPS: {combined_fps}")
            return
        self.timer_interval = int(1000 / combined_fps)
        self.timer.start(self.timer_interval)
        self.is_paused = False
        print(f"Timer started with interval: {self.timer_interval} ms")

        # Update button states
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def pause_videos(self):
        if self.timer.isActive():
            self.timer.stop()
            self.is_paused = True
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            print("Timer paused")

    def stop_videos(self):
        if self.cap1 and self.cap2:
            self.timer.stop()
            self.is_paused = False
            print("Timer stopped and videos reset")

            # Reset frame positions to start
            self.cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)

            # Display first frames
            self.display_initial_frames()

            # Reset seekbar
            self.seek_slider.setValue(0)

            # Update button states
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def update_frames(self):
        try:
            ret1, frame1 = self.cap1.read()
            ret2, frame2 = self.cap2.read()

            if ret1 and ret2:
                if self.is_overlay:
                    self.overlay_label.set_frames(frame1, frame2)
                else:
                    self.display_frame(frame1, self.video_label_1)
                    self.display_frame(frame2, self.video_label_2)

                # Calculate current position in milliseconds
                pos1 = self.cap1.get(cv2.CAP_PROP_POS_MSEC)
                pos2 = self.cap2.get(cv2.CAP_PROP_POS_MSEC)
                current_pos = min(pos1, pos2)
                print(f"Current playback position: {current_pos / 1000:.2f} seconds")

                # Update seekbar without triggering the sliderMoved signal
                self.seek_slider.blockSignals(True)
                self.seek_slider.setValue(int(current_pos))
                self.seek_slider.blockSignals(False)

                # Check if any video has ended
                if (pos1 >= self.duration1 * 1000) or (pos2 >= self.duration2 * 1000):
                    self.stop_videos()

            else:
                # If any video ends, stop playback
                self.stop_videos()

        except cv2.error as e:
            logging.error(f"OpenCV error during frame update: {e}")
            self.stop_videos()
            QMessageBox.critical(
                self, "Error", f"An error occurred during playback:\n{str(e)}"
            )
        except Exception as e:
            logging.error(f"Unexpected error during frame update: {e}")
            self.stop_videos()
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred during playback:\n{str(e)}",
            )

    # Updated seekbar-related methods
    def seek_videos(self, position):
        try:
            if self.cap1 and self.cap2:
                print(f"Seekbar moved to position: {position / 1000} seconds")
                # Set the position in milliseconds
                self.cap1.set(cv2.CAP_PROP_POS_MSEC, position)
                self.cap2.set(cv2.CAP_PROP_POS_MSEC, position)

                # Read and display the frame at the new position
                ret1, frame1 = self.cap1.read()
                ret2, frame2 = self.cap2.read()

                if ret1 and ret2:
                    if self.is_overlay:
                        self.overlay_label.set_frames(frame1, frame2)
                    else:
                        self.display_frame(frame1, self.video_label_1)
                        self.display_frame(frame2, self.video_label_2)

        except cv2.error as e:
            logging.error(f"OpenCV error during seeking: {e}")
            QMessageBox.critical(
                self, "Error", f"An error occurred while seeking:\n{str(e)}"
            )
        except Exception as e:
            logging.error(f"Unexpected error during seeking: {e}")
            QMessageBox.critical(
                self, "Error", f"An unexpected error occurred while seeking:\n{str(e)}"
            )

    def start_seek(self):
        """Pause playback when user starts dragging the seekbar."""
        if self.timer.isActive():
            self.timer.stop()
            self.is_paused = True
            print("Playback paused for seeking")

    def end_seek(self):
        """Resume playback after seek operation."""
        if (
            not self.is_paused
            and hasattr(self, "timer_interval")
            and self.timer_interval > 0
        ):
            self.timer.start(self.timer_interval)
            print("Playback resumed after seeking")

    def on_division_changed(self, division):
        """Handle division changes from the OverlayVideoLabel."""
        # This method can be used to update other UI elements if needed
        print(f"Divider set to {division * 100:.2f}%")

    def closeEvent(self, event):
        # Release video captures if they exist
        if self.cap1:
            self.cap1.release()
        if self.cap2:
            self.cap2.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoCompareApp()
    window.show()
    sys.exit(app.exec())
