import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.popup import Popup

# === База данных ===
db_name = "teacher_assistant.db"

def init_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            question TEXT,
            answer TEXT
        )
    """)

    # Таблица групп
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT UNIQUE NOT NULL
        )
    """)

    # Таблица оценок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            grade INTEGER NOT NULL,
            date_assigned DATE NOT NULL
        )
    """)

    # Добавление администратора
    cursor.execute("""
        INSERT OR IGNORE INTO users (login, password, name, role, question, answer)
        VALUES ('admin', 'admin', 'Administrator', 'admin', NULL, NULL)
    """)

    conn.commit()
    conn.close()

def group_exists(group_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups WHERE group_name = ?", (group_name,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_grade(student_name, group_name, grade):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO grades (student_name, group_name, grade, date_assigned)
        VALUES (?, ?, ?, ?)
    """, (student_name, group_name, grade, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

def get_user(login, password):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users WHERE login = ? AND password = ?
    """, (login, password))
    user = cursor.fetchone()
    conn.close()
    return user

# === Экраны ===
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.login_input = TextInput(hint_text="Логин", multiline=False)
        self.password_input = TextInput(hint_text="Пароль", password=True, multiline=False)
        self.login_button = Button(text="Войти", on_press=self.login)

        layout.add_widget(self.login_input)
        layout.add_widget(self.password_input)
        layout.add_widget(self.login_button)
        self.add_widget(layout)

    def login(self, instance):
        login = self.login_input.text
        password = self.password_input.text
        user = get_user(login, password)

        if user:
            self.manager.current = 'chat'
            chat_screen = self.manager.get_screen('chat')
            chat_screen.user = user
            chat_screen.add_message(f"Добро пожаловать, {user[3]}!")
            chat_screen.add_message("Доступные команды:")
            chat_screen.add_message("- выставить оценку")
            chat_screen.add_message("- расписание")
            chat_screen.add_message("- добавить задание")
        else:
            popup = Popup(title="Ошибка", content=Label(text="Неверный логин или пароль"), size_hint=(0.5, 0.5))
            popup.open()

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.current_command = None
        self.temp_data = {}

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.messages = BoxLayout(orientation='vertical', size_hint_y=None)
        self.messages.bind(minimum_height=self.messages.setter('height'))
        self.scroll.add_widget(self.messages)

        input_layout = BoxLayout(size_hint=(1, 0.2), spacing=5)
        self.input_field = TextInput(hint_text="Введите сообщение", multiline=False)
        self.send_button = Button(text="Отправить", on_press=self.process_message)

        input_layout.add_widget(self.input_field)
        input_layout.add_widget(self.send_button)

        layout.add_widget(self.scroll)
        layout.add_widget(input_layout)
        self.add_widget(layout)

    def add_message(self, message, sender="Бот"):
        self.messages.add_widget(Label(text=f"{sender}: {message}", size_hint_y=None, height=40))

    def process_message(self, instance):
        message = self.input_field.text.strip().lower()
        self.add_message(message, sender="Вы")
        self.input_field.text = ""

        if self.current_command == "grade":
            self.process_grade_input(message)
        else:
            self.process_command(message)

    def process_command(self, message):
        if message == "выставить оценку":
            self.current_command = "grade"
            self.temp_data = {}
            self.add_message("Введите ФИО студента.")
        elif message == "расписание":
            self.add_message("Ваше расписание (пока не реализовано).")
        elif message == "добавить задание":
            self.add_message("Добавьте домашнее задание (пока не реализовано).")
        else:
            self.add_message("Неизвестная команда. Попробуйте снова.")

    def process_grade_input(self, message):
        if "student_name" not in self.temp_data:
            self.temp_data["student_name"] = message
            self.add_message("Введите название группы.")
        elif "group_name" not in self.temp_data:
            self.temp_data["group_name"] = message
            if group_exists(message):
                self.add_message("Введите оценку.")
            else:
                self.add_message("Группа не найдена. Попробуйте заново.")
                self.current_command = None
        elif "grade" not in self.temp_data:
            try:
                grade = int(message)
                if 1 <= grade <= 5:
                    self.temp_data["grade"] = grade
                    save_grade(
                        self.temp_data["student_name"],
                        self.temp_data["group_name"],
                        self.temp_data["grade"]
                    )
                    self.add_message(f"Оценка {grade} для {self.temp_data['student_name']} из группы {self.temp_data['group_name']} сохранена.")
                    self.current_command = None
                else:
                    self.add_message("Оценка должна быть числом от 1 до 5. Попробуйте снова.")
            except ValueError:
                self.add_message("Некорректный формат оценки. Введите число от 1 до 5.")
        else:
            self.add_message("Произошла ошибка. Начните заново.")
            self.current_command = None

# === Основное приложение ===
class TeacherAssistantApp(App):
    def build(self):
        init_db()
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ChatScreen(name='chat'))
        return sm

if __name__ == '__main__':
    TeacherAssistantApp().run()