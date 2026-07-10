import cv2

from PyQt6.QtGui import QImage, QPixmap


class PreviewEngine:

    @staticmethod
    def frame_to_pixmap(frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w, ch = rgb.shape

        bytes_per_line = ch * w

        image = QImage(
            rgb.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        return QPixmap.fromImage(image)