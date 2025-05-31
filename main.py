import sys
import decimal
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QLineEdit,
    QComboBox, QDialog, QSpinBox, QGroupBox, QGridLayout, QFrame, 
    QTableWidget, QHeaderView, QAbstractItemView, QSizePolicy, QTableWidgetItem
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression
import pyodbc

# Константы стиля
FONT_FAMILY = "Bahnschrift Light SemiCondensed"
COLOR_BG_MAIN = "#BBDCFA"
COLOR_BG_ALT = "#FFFFFF"
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

# Функция для подсчёта стоимости заявки с учетом брака материала
def calculate_request_cost(cursor, partner_name):
    try:
        query = """
        SELECT 
            SUM(rp.[Количество] * p.[Минимальная стоимость для партнера] * 
                (1 + COALESCE(m.[Процент брака материала], 0) / 100.0)
        FROM [Запросы партнеров] rp
        JOIN [Продукция] p ON rp.[Продукция] = p.[Наименование продукции]
        JOIN [Типы продукции] tp ON p.[Тип продукции] = tp.[Тип продукции]
        JOIN [Типы материалов] m ON tp.[Тип продукции] = m.[Тип материала]
        WHERE rp.[Партнер] = ?
        """
        cursor.execute(query, partner_name)
        result = cursor.fetchone()
        total = result[0] if result[0] is not None else 0
        total = max(decimal.Decimal(total).quantize(decimal.Decimal('0.01')), decimal.Decimal('0.00'))
        return total
    except Exception as e:
        # Fallback на случай ошибки
        print(f"Ошибка расчета стоимости с учетом брака: {str(e)}")
        try:
            query_fallback = """
            SELECT SUM(rp.[Количество] * p.[Минимальная стоимость для партнера])
            FROM [Запросы партнеров] rp
            JOIN [Продукция] p ON rp.[Продукция] = p.[Наименование продукции]
            WHERE rp.[Партнер] = ?
            """
            cursor.execute(query_fallback, partner_name)
            result = cursor.fetchone()
            total = result[0] if result[0] is not None else 0
            total = max(decimal.Decimal(total).quantize(decimal.Decimal('0.01')), decimal.Decimal('0.00'))
            return total
        except Exception as e2:
            print(f"Ошибка fallback расчета: {str(e2)}")
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
        self.delete_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-family: {FONT_FAMILY}; font-size: 14px;")
        self.delete_btn.clicked.connect(self.delete_selected_request)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        main_layout.addWidget(self.list_widget)

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
        self.materials_defect = {}
        self.request_items = []
        self.custom_type_visible = False
        self.init_ui()
        self.load_products_and_defects()
        if self.partner_name:
            self.load_partner_data()
            self.load_request_items()
        else:
            self.rating_spin.setValue(100)
            self.custom_type_edit.hide()
            self.custom_type_label.hide()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Сворачиваемый блок данных партнера
        self.partner_group = QGroupBox("Данные партнера")
        self.partner_group.setCheckable(True)
        self.partner_group.setChecked(True if not self.partner_name else False)
        self.partner_group.toggled.connect(self.on_partner_group_toggled)
        partner_layout = QGridLayout()
        partner_layout.setVerticalSpacing(5)
        
        # Основные данные
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
        
        # Кнопка для дополнительных полей
        self.more_btn = QPushButton("Дополнительно ▼")
        self.more_btn.setStyleSheet("text-align:left; border:none; color: #0C4882;")
        self.more_btn.clicked.connect(self.toggle_additional_fields)
        partner_layout.addWidget(self.more_btn, 4, 0, 1, 2)
        
        # Дополнительные поля (скрыты по умолчанию)
        self.additional_fields = []
        
        inn_label = QLabel("ИНН:")
        self.inn_edit = QLineEdit()
        self.inn_edit.setPlaceholderText("10 цифр")
        regex = QRegularExpression("^[0-9]{10}$")
        validator = QRegularExpressionValidator(regex, self.inn_edit)
        self.inn_edit.setValidator(validator)
        partner_layout.addWidget(inn_label, 5, 0)
        partner_layout.addWidget(self.inn_edit, 5, 1)
        self.additional_fields.extend([inn_label, self.inn_edit])
        
        address_label = QLabel("Юридический адрес:")
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("г. Москва, ул. Ленина, д. 1")
        partner_layout.addWidget(address_label, 6, 0)
        partner_layout.addWidget(self.address_edit, 6, 1)
        self.additional_fields.extend([address_label, self.address_edit])
        
        phone_label = QLabel("Телефон:")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 (XXX) XXX-XX-XX")
        partner_layout.addWidget(phone_label, 7, 0)
        partner_layout.addWidget(self.phone_edit, 7, 1)
        self.additional_fields.extend([phone_label, self.phone_edit])
        
        email_label = QLabel("Email:")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@domain.com")
        partner_layout.addWidget(email_label, 8, 0)
        partner_layout.addWidget(self.email_edit, 8, 1)
        self.additional_fields.extend([email_label, self.email_edit])
        
        rating_label = QLabel("Рейтинг:")
        self.rating_spin = QSpinBox()
        self.rating_spin.setMinimum(0)
        self.rating_spin.setMaximum(1000)
        partner_layout.addWidget(rating_label, 9, 0)
        partner_layout.addWidget(self.rating_spin, 9, 1)
        self.additional_fields.extend([rating_label, self.rating_spin])
        
        # Скрыть дополнительные поля при создании новой заявки
        if not self.partner_name:
            for field in self.additional_fields:
                field.hide()
        
        self.partner_group.setLayout(partner_layout)
        main_layout.addWidget(self.partner_group)
        
        # Продукция в заявке
        products_group = QGroupBox("Продукция в заявке")
        products_layout = QVBoxLayout()
        products_layout.setSpacing(5)
        
        # Компактный интерфейс добавления продукции
        add_product_layout = QHBoxLayout()
        
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)
        add_product_layout.addWidget(self.product_combo)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(1000000)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setMaximumWidth(100)
        add_product_layout.addWidget(self.quantity_spin)
        
        self.add_product_btn = QPushButton("Добавить")
        self.add_product_btn.clicked.connect(self.add_product)
        self.add_product_btn.setMaximumWidth(100)
        add_product_layout.addWidget(self.add_product_btn)
        
        products_layout.addLayout(add_product_layout)
        
        # Таблица продукции
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Продукция", "Количество", "Стоимость с учетом брака"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        products_layout.addWidget(self.table)
        
        # Кнопки управления таблицей
        table_btn_layout = QHBoxLayout()
        self.remove_product_btn = QPushButton("Удалить выбранное")
        self.remove_product_btn.clicked.connect(self.remove_selected_product)
        self.remove_product_btn.setMaximumWidth(150)
        table_btn_layout.addWidget(self.remove_product_btn)
        
        table_btn_layout.addStretch()
        products_layout.addLayout(table_btn_layout)
        
        products_group.setLayout(products_layout)
        main_layout.addWidget(products_group)
        
        # Итоговая стоимость
        self.total_cost_label = QLabel("Итоговая стоимость: 0.00 ₽")
        self.total_cost_label.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        self.total_cost_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.total_cost_label)
        
        # Кнопки сохранения/отмены
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white;")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setMinimumWidth(120)
        self.save_btn.clicked.connect(self.save_request)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet("background-color: {COLOR_ACCENT}; color: white;")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # Блокировка данных партнера при редактировании
        if self.partner_name:
            self.partner_group.setEnabled(False)
            self.more_btn.hide()

    def on_partner_group_toggled(self, checked):
        # При сворачивании блока скрываем все дочерние элементы
        for i in range(self.partner_group.layout().count()):
            item = self.partner_group.layout().itemAt(i)
            if item.widget():
                item.widget().setVisible(checked)
        
        # Всегда показываем кнопку "Дополнительно"
        self.more_btn.setVisible(True)
        
        # Обновляем текст кнопки
        self.more_btn.setText("Дополнительно ▼" if checked else "Дополнительно ▲")

    def toggle_additional_fields(self):
        visible = not self.additional_fields[0].isVisible()
        for field in self.additional_fields:
            field.setVisible(visible)
        
        # Обновляем текст кнопки
        self.more_btn.setText("Дополнительно ▲" if visible else "Дополнительно ▼")
        
        # Изменяем размер диалога
        self.adjustSize()

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

    def load_products_and_defects(self):
        cursor = self.conn.cursor()
        try:
            # Загрузка процентов брака материалов
            cursor.execute("SELECT [Тип материала], [Процент брака материала] FROM [Типы материалов]")
            for row in cursor.fetchall():
                self.materials_defect[row[0]] = row[1]
            
            # Загрузка продукции с типами
            cursor.execute("""
                SELECT p.[Наименование продукции], p.[Минимальная стоимость для партнера], tp.[Тип продукции]
                FROM [Продукция] p
                JOIN [Типы продукции] tp ON p.[Тип продукции] = tp.[Тип продукции]
            """)
            self.products = cursor.fetchall()
            self.product_combo.clear()
            for p in self.products:
                self.product_combo.addItem(p[0])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки данных", f"Не удалось загрузить данные продукции:\n{str(e)}")
            self.products = []

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
                else:
                    self.type_combo.setCurrentText("Другой")
                    self.custom_type_edit.setText(partner_type)
                
                self.name_edit.setText(self.partner_name)
                self.director_edit.setText(partner_data[1])
                self.address_edit.setText(partner_data[2])
                self.phone_edit.setText(partner_data[3])
                self.email_edit.setText(partner_data[4])
                self.rating_spin.setValue(partner_data[5])
                self.inn_edit.setText(partner_data[6])
                
                # Показать все поля при редактировании
                for field in self.additional_fields:
                    field.show()
            else:
                QMessageBox.warning(self, "Ошибка", "Партнер не найден в базе данных")
                self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при загрузке данных партнера:\n{str(e)}")
            self.reject()

    def validate_partner_data(self):
        # Проверяем только видимые поля
        errors = []
        
        if self.name_edit.isVisible() and not self.name_edit.text().strip():
            errors.append("Наименование партнера не может быть пустым")
        
        if self.director_edit.isVisible() and not self.director_edit.text().strip():
            errors.append("ФИО директора не может быть пустым")
            
        if self.inn_edit.isVisible():
            inn = self.inn_edit.text().strip()
            if not inn:
                errors.append("ИНН не может быть пустым")
            elif len(inn) != 10 or not inn.isdigit():
                errors.append("ИНН должен состоять из 10 цифр")
            
        if self.type_combo.currentText() == "Другой" and self.custom_type_edit.isVisible() and not self.custom_type_edit.text().strip():
            errors.append("Укажите тип партнера")
            
        if errors:
            QMessageBox.warning(self, "Ошибки в данных", "\n".join(errors))
            return False
            
        return True

    def load_request_items(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT [Продукция], [Количество] FROM [Запросы партнеров] WHERE [Партнер] = ?", 
            self.partner_name
        )
        self.request_items = cursor.fetchall()
        self.table.setRowCount(0)
        for product_name, quantity in self.request_items:
            self.add_product_to_table(product_name, quantity)

    def add_product(self):
        product_name = self.product_combo.currentText()
        quantity = self.quantity_spin.value()
        
        # Проверяем, не добавлен ли уже этот продукт
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == product_name:
                QMessageBox.warning(self, "Дублирование", "Этот продукт уже добавлен в заявку")
                return
                
        self.add_product_to_table(product_name, quantity)
        self.quantity_spin.setValue(1)

    def add_product_to_table(self, product_name, quantity):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Название продукта
        name_item = QTableWidgetItem(product_name)
        self.table.setItem(row, 0, name_item)
        
        # Количество
        quantity_item = QTableWidgetItem(str(quantity))
        quantity_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, quantity_item)
        
        # Стоимость с учетом брака материала
        cost = self.calculate_product_cost(product_name, quantity)
        cost_item = QTableWidgetItem(f"{cost:.2f} ₽")
        cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 2, cost_item)
        
        self.update_total_cost()

    def calculate_product_cost(self, product_name, quantity):
        """Расчет стоимости с учетом процента брака материала"""
        try:
            # Находим продукт
            product = next(p for p in self.products if p[0] == product_name)
            base_cost = float(product[1])
            product_type = product[2]
            
            # Получаем процент брака для типа материала
            defect_percent = self.materials_defect.get(product_type, 0.0)
            
            # Рассчитываем стоимость с учетом брака
            adjusted_cost = base_cost * (1 + defect_percent / 100.0)
            total_cost = adjusted_cost * quantity
            return total_cost
        except Exception as e:
            print(f"Ошибка расчета стоимости продукта: {str(e)}")
            # Fallback: базовая стоимость без учета брака
            product = next(p for p in self.products if p[0] == product_name)
            return float(product[1]) * quantity

    def remove_selected_product(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Удаление продукта", "Пожалуйста, выберите продукт для удаления.")
            return
            
        for row in sorted([index.row() for index in selected_rows], reverse=True):
            self.table.removeRow(row)
            
        self.update_total_cost()

    def update_total_cost(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            cost_text = self.table.item(row, 2).text().replace(" ₽", "")
            total += float(cost_text)
            
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
            email = self.email_edit.text().strip() if self.email_edit.isVisible() else ""
            phone = self.phone_edit.text().strip() if self.phone_edit.isVisible() else ""
            address = self.address_edit.text().strip() if self.address_edit.isVisible() else ""
            inn = self.inn_edit.text().strip() if self.inn_edit.isVisible() else ""
            rating = self.rating_spin.value() if self.rating_spin.isVisible() else 100
            
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
                # При редактировании обновляем только рейтинг
                cursor.execute("""
                    UPDATE [Партнеры] SET [Рейтинг] = ?
                    WHERE [Наименование партнера] = ?
                """, (rating, self.partner_name))
            
            # Обновляем список продукции
            cursor.execute("DELETE FROM [Запросы партнеров] WHERE [Партнер] = ?", self.partner_name)
            
            for row in range(self.table.rowCount()):
                product_name = self.table.item(row, 0).text()
                quantity = int(self.table.item(row, 1).text())
                
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