import sys
import decimal
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QLineEdit,
    QComboBox, QDialog, QSpinBox, QGroupBox, QGridLayout, QFrame, 
    QTableWidget, QHeaderView, QAbstractItemView
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression
import pyodbc

# Константы стиля
FONT_FAMILY = "Bahnschrift Light SemiCondensed"
COLOR_BG_MAIN = "#FFFFFF"
COLOR_BG_ALT = "#BBDCFA"
COLOR_ACCENT = "#0C4882"

# Подключение к базе данных MS SQL Server
def create_connection():
    try:
        conn = pyodbc.connect(
            r"DRIVER={ODBC Driver 17 for SQL Server};"
            r"SERVER=DESKTOP-V870T0J\SQLEXPRESS;"
            r"DATABASE=PartnerProductsDB;"
            r"Trusted_Connection=yes;"
        )
        return conn
    except Exception as e:
        QMessageBox.critical(None, "Ошибка подключения к БД",
                             f"Не удалось подключиться к базе данных.\n\n{str(e)}")
        sys.exit(1)

# Функция для подсчёта стоимости заявки
def calculate_request_cost(cursor, partner_name):
    try:
        query = """
        SELECT SUM(rp.[Количество] * p.[Минимальная стоимость для партнера])
        FROM [Запросы партнеров] rp
        JOIN [Продукция] p ON rp.[Продукция] = p.[Наименование продукции]
        WHERE rp.[Партнер] = ?
        """
        cursor.execute(query, partner_name)
        result = cursor.fetchone()
        total = result[0] if result[0] is not None else 0
        total = max(decimal.Decimal(total).quantize(decimal.Decimal('0.01')), decimal.Decimal('0.00'))
        return total
    except Exception as e:
        return decimal.Decimal('0.00')

# Виджет для отображения одной заявки
class RequestItemWidget(QWidget):
    def __init__(self, partner_data, cost):
        super().__init__()
        self.partner_data = partner_data
        self.cost = cost
        self.init_ui()

    def init_ui(self):
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(10, 10, 10, 10)

        v_left = QVBoxLayout()
        top_label = QLabel(f"<b>{self.partner_data['Тип партнера']}</b> | <b>{self.partner_data['Наименование партнера']}</b>")
        top_label.setFont(QFont(FONT_FAMILY, 11))
        v_left.addWidget(top_label)

        addr_label = QLabel(self.partner_data['Юридический адрес партнера'])
        addr_label.setFont(QFont(FONT_FAMILY, 9))
        v_left.addWidget(addr_label)

        phone_label = QLabel(self.partner_data['Телефон партнера'])
        phone_label.setFont(QFont(FONT_FAMILY, 9))
        v_left.addWidget(phone_label)

        rating_label = QLabel(f"Рейтинг: {self.partner_data['Рейтинг']}")
        rating_label.setFont(QFont(FONT_FAMILY, 9))
        v_left.addWidget(rating_label)

        h_layout.addLayout(v_left)

        cost_label = QLabel(f"<b>Стоимость: {self.cost} ₽</b>")
        cost_label.setFont(QFont(FONT_FAMILY, 11))
        cost_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cost_label.setFixedWidth(150)
        h_layout.addWidget(cost_label)

        self.setLayout(h_layout)
        self.setStyleSheet(f"background-color: {COLOR_BG_ALT}; border: 1px solid #999999;")

# Главное окно приложения
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conn = create_connection()
        self.setWindowTitle("Заявки партнеров - Новые технологии")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.load_requests()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        logo_label = QLabel()
        pixmap = QPixmap("icon.ico")
        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.edit_request)
        main_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Добавить заявку")
        self.add_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-family: {FONT_FAMILY}; font-size: 14px;")
        self.add_btn.clicked.connect(self.add_request)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Редактировать заявку")
        self.edit_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-family: {FONT_FAMILY}; font-size: 14px;")
        self.edit_btn.clicked.connect(self.edit_selected_request)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Удалить заявку")
        self.delete_btn.setStyleSheet(f"background-color: #D9534F; color: white; font-family: {FONT_FAMILY}; font-size: 14px;")
        self.delete_btn.clicked.connect(self.delete_selected_request)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setStyleSheet(f"background-color: {COLOR_BG_MAIN}; font-family: {FONT_FAMILY}; color: black;")

    def load_requests(self):
        self.list_widget.clear()
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT p.*
                FROM [Партнеры] p
                JOIN [Запросы партнеров] rp ON p.[Наименование партнера] = rp.[Партнер]
            """)
            partners = cursor.fetchall()
            for p in partners:
                partner_data = {
                    "Наименование партнера": p[0],
                    "Тип партнера": p[1],
                    "Директор": p[2],
                    "Электронная почта партнера": p[3],
                    "Телефон партнера": p[4],
                    "Юридический адрес партнера": p[5],
                    "ИНН": p[6],
                    "Рейтинг": p[7]
                }
                cost = calculate_request_cost(cursor, partner_data["Наименование партнера"])
                item_widget = RequestItemWidget(partner_data, cost)
                item = QListWidgetItem(self.list_widget)
                item.setSizeHint(item_widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, item_widget)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки данных", f"Не удалось загрузить данные из базы:\n{str(e)}")

    def add_request(self):
        dialog = RequestEditDialog(self.conn, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_requests()

    def edit_selected_request(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Выбор заявки", "Пожалуйста, выберите заявку для редактирования.")
            return
        item = selected_items[0]
        widget = self.list_widget.itemWidget(item)
        if widget:
            partner_name = widget.partner_data["Наименование партнера"]
            dialog = RequestEditDialog(self.conn, partner_name=partner_name, parent=self)
            if dialog.exec() == QDialog.Accepted:
                self.load_requests()

    def delete_selected_request(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Удаление заявки", "Пожалуйста, выберите заявку для удаления.")
            return
        item = selected_items[0]
        widget = self.list_widget.itemWidget(item)
        if not widget:
            return
        partner_name = widget.partner_data["Наименование партнера"]
        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить все заявки партнера '{partner_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM [Запросы партнеров] WHERE [Партнер] = ?", partner_name)
                cursor.execute("DELETE FROM [Партнеры] WHERE [Наименование партнера] = ?", partner_name)
                self.conn.commit()
                self.load_requests()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при удалении данных:\n{str(e)}")

    def edit_request(self, item):
        widget = self.list_widget.itemWidget(item)
        if widget:
            partner_name = widget.partner_data["Наименование партнера"]
            dialog = RequestEditDialog(self.conn, partner_name=partner_name, parent=self)
            if dialog.exec() == QDialog.Accepted:
                self.load_requests()

# Диалог редактирования заявок
class RequestEditDialog(QDialog):
    def __init__(self, conn, partner_name=None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.partner_name = partner_name
        self.setWindowTitle("Заявка партнера" if partner_name else "Новая заявка партнера")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.products = []
        self.request_items = []
        self.custom_type_visible = False
        self.init_ui()
        self.load_products()
        if self.partner_name:
            self.load_partner_data()
            self.load_request_items()
        else:
            self.rating_spin.setValue(100)
            self.custom_type_edit.hide()
            self.custom_type_label.hide()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        partner_group = QGroupBox("Данные партнера")
        partner_layout = QGridLayout()
        
        partner_layout.addWidget(QLabel("Тип партнера:"), 0, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Оптовый", "Розничный", "Интернет-магазин", "Другой"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        partner_layout.addWidget(self.type_combo, 0, 1)
        
        self.custom_type_label = QLabel("Укажите свой тип:")
        self.custom_type_label.hide()
        partner_layout.addWidget(self.custom_type_label, 1, 0)
        
        self.custom_type_edit = QLineEdit()
        self.custom_type_edit.hide()
        self.custom_type_edit.setPlaceholderText("Введите тип партнера")
        partner_layout.addWidget(self.custom_type_edit, 1, 1)
        
        partner_layout.addWidget(QLabel("Наименование:"), 2, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ромашка")
        partner_layout.addWidget(self.name_edit, 2, 1)
        
        partner_layout.addWidget(QLabel("ФИО директора:"), 3, 0)
        self.director_edit = QLineEdit()
        self.director_edit.setPlaceholderText("Иванов Иван Иванович")
        partner_layout.addWidget(self.director_edit, 3, 1)
        
        partner_layout.addWidget(QLabel("ИНН:"), 4, 0)
        self.inn_edit = QLineEdit()
        self.inn_edit.setPlaceholderText("10 цифр")
        # Исправленная валидация ИНН
        regex = QRegularExpression("^[0-9]{10}$")
        validator = QRegularExpressionValidator(regex, self.inn_edit)
        self.inn_edit.setValidator(validator)
        partner_layout.addWidget(self.inn_edit, 4, 1)
        
        partner_layout.addWidget(QLabel("Юридический адрес:"), 5, 0)
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("г. Москва, ул. Ленина, д. 1")
        partner_layout.addWidget(self.address_edit, 5, 1)
        
        partner_layout.addWidget(QLabel("Телефон:"), 6, 0)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 (XXX) XXX-XX-XX")
        partner_layout.addWidget(self.phone_edit, 6, 1)
        
        partner_layout.addWidget(QLabel("Email:"), 7, 0)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@domain.com")
        partner_layout.addWidget(self.email_edit, 7, 1)
        
        partner_layout.addWidget(QLabel("Рейтинг:"), 8, 0)
        self.rating_spin = QSpinBox()
        self.rating_spin.setMinimum(0)
        self.rating_spin.setMaximum(1000)
        partner_layout.addWidget(self.rating_spin, 8, 1)
        
        partner_group.setLayout(partner_layout)
        main_layout.addWidget(partner_group)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        products_group = QGroupBox("Продукция в заявке")
        products_layout = QVBoxLayout()
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Продукция", "Количество", "Минимальная стоимость"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        products_layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton("Добавить продукт")
        self.add_product_btn.clicked.connect(self.add_product_row)
        btn_layout.addWidget(self.add_product_btn)
        
        self.remove_product_btn = QPushButton("Удалить продукт")
        self.remove_product_btn.clicked.connect(self.remove_selected_product)
        btn_layout.addWidget(self.remove_product_btn)
        
        products_layout.addLayout(btn_layout)
        products_group.setLayout(products_layout)
        main_layout.addWidget(products_group)
        
        self.total_cost_label = QLabel("Итоговая стоимость: 0.00 ₽")
        self.total_cost_label.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        main_layout.addWidget(self.total_cost_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white;")
        self.save_btn.clicked.connect(self.save_request)
        self.save_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet("background-color: #D9534F; color: white;")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        if self.partner_name:
            self.type_combo.setEnabled(False)
            self.name_edit.setEnabled(False)
            self.director_edit.setEnabled(False)
            self.inn_edit.setEnabled(False)
            self.address_edit.setEnabled(False)
            self.phone_edit.setEnabled(False)
            self.email_edit.setEnabled(False)
            self.rating_spin.setEnabled(False)
            self.custom_type_edit.setEnabled(False)

    def on_type_changed(self, index):
        selected_type = self.type_combo.currentText()
        if selected_type == "Другой":
            self.custom_type_label.show()
            self.custom_type_edit.show()
            self.custom_type_edit.setFocus()
        else:
            self.custom_type_label.hide()
            self.custom_type_edit.hide()

    def get_selected_type(self):
        if self.type_combo.currentText() == "Другой":
            return self.custom_type_edit.text().strip()
        return self.type_combo.currentText()

    def load_partner_data(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT [Тип партнера], [Директор], [Юридический адрес партнера], "
                "[Телефон партнера], [Электронная почта партнера], [Рейтинг], [ИНН] "
                "FROM [Партнеры] WHERE [Наименование партнера] = ?", 
                self.partner_name
            )
            partner_data = cursor.fetchone()
            
            if partner_data:
                partner_type = partner_data[0]
                if partner_type in ["Оптовый", "Розничный", "Интернет-магазин"]:
                    self.type_combo.setCurrentText(partner_type)
                    self.custom_type_label.hide()
                    self.custom_type_edit.hide()
                else:
                    self.type_combo.setCurrentText("Другой")
                    self.custom_type_edit.setText(partner_type)
                    self.custom_type_label.show()
                    self.custom_type_edit.show()
                
                self.name_edit.setText(self.partner_name)
                self.director_edit.setText(partner_data[1])
                self.address_edit.setText(partner_data[2])
                self.phone_edit.setText(partner_data[3])
                self.email_edit.setText(partner_data[4])
                self.rating_spin.setValue(partner_data[5])
                self.inn_edit.setText(partner_data[6])
            else:
                QMessageBox.warning(self, "Ошибка", "Партнер не найден в базе данных")
                self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при загрузке данных партнера:\n{str(e)}")
            self.reject()

    def validate_partner_data(self):
        errors = []
        
        if not self.name_edit.text().strip():
            errors.append("Наименование партнера не может быть пустым")
        
        if not self.director_edit.text().strip():
            errors.append("ФИО директора не может быть пустым")
            
        inn = self.inn_edit.text().strip()
        if not inn:
            errors.append("ИНН не может быть пустым")
        elif len(inn) != 12 or not inn.isdigit():
            errors.append("ИНН должен состоять из 10 цифр")
            
        if not self.address_edit.text().strip():
            errors.append("Юридический адрес не может быть пустым")
            
        if not self.phone_edit.text().strip():
            errors.append("Телефон не может быть пустым")
            
        email = self.email_edit.text().strip()
        if not email:
            errors.append("Email не может быть пустым")
        elif "@" not in email or "." not in email:
            errors.append("Некорректный формат email")
            
        if self.rating_spin.value() < 0:
            errors.append("Рейтинг должен быть положительным числом")
            
        if self.type_combo.currentText() == "Другой" and not self.custom_type_edit.text().strip():
            errors.append("Укажите тип партнера")
            
        if errors:
            QMessageBox.warning(self, "Ошибки в данных", "\n".join(errors))
            return False
            
        return True

    def load_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT [Наименование продукции], [Минимальная стоимость для партнера] FROM [Продукция]")
        self.products = cursor.fetchall()

    def load_request_items(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT [Продукция], [Количество] FROM [Запросы партнеров] WHERE [Партнер] = ?", 
            self.partner_name
        )
        self.request_items = cursor.fetchall()
        self.table.setRowCount(0)
        for product_name, quantity in self.request_items:
            self.add_product_row(product_name, quantity)

    def add_product_row(self, product_name=None, quantity=None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox()
        for p in self.products:
            combo.addItem(p[0])
        if product_name:
            index = combo.findText(product_name)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(self.update_total_cost)
        self.table.setCellWidget(row, 0, combo)

        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(1000000)
        spin.setValue(quantity if quantity else 1)
        spin.valueChanged.connect(self.update_total_cost)
        self.table.setCellWidget(row, 1, spin)

        cost_label = QLabel()
        self.table.setCellWidget(row, 2, cost_label)

        self.update_row_cost(row)
        self.update_total_cost()

    def remove_selected_product(self):
        selected_rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        if not selected_rows:
            QMessageBox.warning(self, "Удаление продукта", "Пожалуйста, выберите продукт для удаления.")
            return
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)
        self.update_total_cost()

    def update_row_cost(self, row):
        combo = self.table.cellWidget(row, 0)
        cost_label = self.table.cellWidget(row, 2)
        product_name = combo.currentText()
        cost = next((float(p[1]) for p in self.products if p[0] == product_name))
        cost_label.setText(f"{cost:.2f} ₽")

    def update_total_cost(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 0)
            spin = self.table.cellWidget(row, 1)
            product_name = combo.currentText()
            quantity = spin.value()
            cost = next((float(p[1]) for p in self.products if p[0] == product_name))
            total += cost * quantity
            self.update_row_cost(row)
        self.total_cost_label.setText(f"Итоговая стоимость: {total:.2f} ₽")

    def save_request(self):
        if not self.validate_partner_data():
            return
            
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один продукт в заявку.")
            return
            
        cursor = self.conn.cursor()
        try:
            partner_name = self.name_edit.text().strip()
            partner_type = self.get_selected_type()
            director = self.director_edit.text().strip()
            email = self.email_edit.text().strip()
            phone = self.phone_edit.text().strip()
            address = self.address_edit.text().strip()
            inn = self.inn_edit.text().strip()
            rating = self.rating_spin.value()
            
            if not self.partner_name:
                cursor.execute(
                    "SELECT COUNT(*) FROM [Партнеры] WHERE [Наименование партнера] = ?", 
                    partner_name
                )
                if cursor.fetchone()[0] > 0:
                    QMessageBox.warning(self, "Ошибка", "Партнер с таким наименованием уже существует.")
                    return
                
                cursor.execute("""
                    INSERT INTO [Партнеры] (
                        [Наименование партнера], [Тип партнера], [Директор], 
                        [Электронная почта партнера], [Телефон партнера], 
                        [Юридический адрес партнера], [ИНН], [Рейтинг]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    partner_name,
                    partner_type,
                    director,
                    email,
                    phone,
                    address,
                    inn,
                    rating
                ))
                self.partner_name = partner_name
            else:
                cursor.execute("""
                    UPDATE [Партнеры] SET
                    [Тип партнера] = ?, [Директор] = ?, [Электронная почта партнера] = ?, 
                    [Телефон партнера] = ?, [Юридический адрес партнера] = ?, [ИНН] = ?, [Рейтинг] = ?
                    WHERE [Наименование партнера] = ?
                """, (
                    partner_type,
                    director,
                    email,
                    phone,
                    address,
                    inn,
                    rating,
                    self.partner_name
                ))
            
            cursor.execute("DELETE FROM [Запросы партнеров] WHERE [Партнер] = ?", self.partner_name)
            
            for row in range(self.table.rowCount()):
                combo = self.table.cellWidget(row, 0)
                spin = self.table.cellWidget(row, 1)
                product_name = combo.currentText()
                quantity = spin.value()
                
                cursor.execute("""
                    INSERT INTO [Запросы партнеров] (
                        [Продукция], [Партнер], [Количество]
                    ) VALUES (?, ?, ?)
                """, (product_name, self.partner_name, quantity))
            
            self.conn.commit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при сохранении данных:\n{str(e)}")
            self.conn.rollback()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())