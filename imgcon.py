import sys
import os
import zlib
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMainWindow, QAction, QFileDialog, QMessageBox, QStyleFactory, QInputDialog)
from PyQt5.QtGui import QPainter, QColor
from PIL import Image, ImageDraw, ImageFont
import struct

class RGBImageWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.image_matrix = []
        self.cols = 0
        self.rows = 0
        self.pixel_size = 1
        self.x_offset = 0
        self.y_offset = 0
        self.current_file = None
        self.set_initial_image()

    def paintEvent(self, event):
        if not self.image_matrix: return
        painter = QPainter(self)

        for y in range(self.rows):
            for x in range(self.cols):
                r, g, b = self.image_matrix[y][x]
                color = QColor(r, g, b)
                painter.fillRect(
                    self.x_offset + x * self.pixel_size, 
                    self.y_offset + y * self.pixel_size, 
                    self.pixel_size, self.pixel_size, color)

    def resizeEvent(self, event):
        self.update_image_scaling()

    def set_initial_image(self):
        img = Image.new('RGB', (600, 400), color='lightblue')
        draw = ImageDraw.Draw(img)
        for i in range(0, 600, 40):
            draw.line((i, 0, i, 400), fill=(255, 255, 255), width=2)
        for j in range(0, 400, 40):
            draw.line((0, j, 600, j), fill=(255, 255, 255), width=2)
        font_size = 50
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
        text = "TSRImage"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        draw.text(((600 - text_width) // 2, (400 - text_height) // 2), text, fill="white", font=font)
        img = img.resize((int(img.width * 0.5), int(img.height * 0.5)))
        self.cols, self.rows = img.size
        self.image_matrix = []
        img = img.convert('RGB')
        for y in range(self.rows):
            row = []
            for x in range(self.cols):
                r, g, b = img.getpixel((x, y))
                row.append((r, g, b))
            self.image_matrix.append(row)
        self.update_image_scaling()
        self.update()

    def update_image_scaling(self):
        if not self.image_matrix:
            return
        self.pixel_size = min(self.width() // self.cols, self.height() // self.rows)
        self.x_offset = (self.width() - self.cols * self.pixel_size) // 2
        self.y_offset = (self.height() - self.rows * self.pixel_size) // 2

    def save_image(self, filename):
        raw_data = bytearray()
        for row in self.image_matrix:
            for r, g, b in row:
                raw_data.extend([r, g, b])
        header = struct.pack('II', self.cols, self.rows)
        compressed_data = zlib.compress(raw_data, level=9)
        with open(filename, 'wb') as f:
            f.write(header)
            f.write(compressed_data)
        self.current_file = filename

    def load_image(self, filename):
        with open(filename, 'rb') as f:
            header = f.read(8)
            self.cols, self.rows = struct.unpack('II', header)
            compressed_data = f.read()
        raw_data = zlib.decompress(compressed_data)
        self.image_matrix = []
        idx = 0
        for y in range(self.rows):
            row = []
            for x in range(self.cols):
                r = raw_data[idx]
                g = raw_data[idx + 1]
                b = raw_data[idx + 2]
                row.append((r, g, b))
                idx += 3
            self.image_matrix.append(row)
        self.update_image_scaling()
        self.update()
        self.current_file = filename  # Обновляем текущий файл

    def convert_image_to_tsr(self, image_path):
        quality, ok = QInputDialog.getItem(self, "Выбор качества", 
                                           "Выберите уровень качества сжатия:", 
                                           ["100%", "75%", "50%", "25%"], 0, False)
        if not ok: return
        
        img = Image.open(image_path).convert('RGB')
        img = img.resize((int(img.width * 0.5), int(img.height * 0.5)))

        quality_map = {"100%": 256, "75%": 128, "50%": 64, "25%": 32}
        colors = quality_map.get(quality, 256)

        img = img.quantize(colors=colors, method=Image.MEDIANCUT)

        self.cols, self.rows = img.size
        self.image_matrix = []
        img = img.convert('RGB')
        for y in range(self.rows):
            row = []
            for x in range(self.cols):
                r, g, b = img.getpixel((x, y))
                row.append((r, g, b))
            self.image_matrix.append(row)
        self.update_image_scaling()
        self.update()
        self.current_file = image_path  

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSRImage")
        self.setGeometry(100, 100, 800, 600)
        self.image_widget = RGBImageWidget()
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_widget)
        self.setCentralWidget(central_widget)
        self.create_menu()
        self.center_window() 

    def center_window(self):
        frame_geo = self.frameGeometry()
        screen_center = QApplication.desktop().screen().rect().center()
        frame_geo.moveCenter(screen_center)
        self.move(frame_geo.topLeft())

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        load_action = QAction('Открыть...', self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_image)
        file_menu.addAction(load_action)

        save_action = QAction('Сохранить...', self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)
        info_action = QAction('Информация о файле', self)
        info_action.triggered.connect(self.show_file_info)
        file_menu.addAction(info_action)
        convert_action = QAction('Конвертировать...', self)
        convert_action.setShortcut("Ctrl+C")
        convert_action.triggered.connect(self.convert_image_to_tsr)
        file_menu.addAction(convert_action)
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about_info)
        menubar.addAction(about_action)

    def load_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Загрузить изображение", "", "TSR Files (*.tsr);;All Files (*)", options=options)
        if file_name: self.image_widget.load_image(file_name)

    def save_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить изображение", "", "TSR Files (*.tsr);;All Files (*)", options=options)
        if file_name: self.image_widget.save_image(file_name)

    def convert_image_to_tsr(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Image Files (*.png *.jpeg *.jpg);;All Files (*)", options=options)
        if file_name: 
            self.image_widget.convert_image_to_tsr(file_name)

    def show_file_info(self):
        """Показывает информацию о текущем файле."""
        file_path = self.image_widget.current_file
        if file_path:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            if file_size < 1024 * 1024:  # Если размер меньше 1 МБ
                file_size_kb = file_size / 1024  # Перевод в килобайты
                file_info = f"Имя файла: {file_name}\nРазмер файла: {file_size_kb:.2f} КБ"
            else:
                file_size_mb = file_size / (1024 * 1024)  # Перевод в мегабайты
                file_info = f"Имя файла: {file_name}\nРазмер файла: {file_size_mb:.2f} МБ"
            QMessageBox.information(self, "Информация о файле", file_info)
        else:
            QMessageBox.warning(self, "Информация о файле", "Файл не загружен.")

    def show_about_info(self):
        QMessageBox.information(self, "О программе", "TSRImage\n\nКодек изображений .tsr\n\n© shrr18io")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
