import os
import sys
import datetime
import sqlite3

import g4f
from g4f.models import *

from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QGuiApplication, QIcon, QTextCursor, QResizeEvent
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QTextEdit, QComboBox, QFileDialog, QMessageBox,
                             QLineEdit, QDialog, QToolButton)

models = {
        'gpt-3.5 turbo': gpt_35_turbo,
        'gpt-3.5 turbo_0613': gpt_35_turbo_0613,
        'gpt-4': gpt_4,
        'gemini': gemini,
        'blackbox': blackbox,
        'mixtral 8x7b': mixtral_8x7b,
        }


def resource_path(relative_path):
    """
    Gets the absolute path to a resource file.
    Used in the code to keep the window icon after compiling with pyinstaller.

    :param relative_path: The relative path to the resource file.
    :return: The absolute path to the resource file.
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class CustomTextEdit(QTextEdit):
    """
    A custom QTextEdit class that redirects the standard output to the text widget.
    """
    textUpdated = pyqtSignal(str)

    def write(self, text):
        """
        Writes text to the text widget.

        :param text: The text to be written.
        """
        self.insertPlainText(text + '\n\n')
        self.setReadOnly(True)

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        self.setTextCursor(cursor)


class ClearButton(QToolButton):
    """
    The ClearButton class is a button that clears a text field when clicked.
    """
    def __init__(self, text_edit, parent=None):
        """
        Initializes a button with an icon and a tooltip.
        Connects the clicked signal to the clear slot of the text field.

        :param text_edit (QTextEdit): The text field to clear.
        :param parent (QWidget, optional): The parent widget for this button. Default is None.
        """
        super().__init__(parent)
        self.setIcon(QIcon(resource_path('clear.png')))
        self.setIconSize(QSize(14, 14))
        self.setToolTip("Clear Input")
        self.clicked.connect(lambda: text_edit.clear())


class ClearLogButton(QToolButton):
    """
    The ClearLogButton class is a button that clears the output text field when clicked.
    """
    def __init__(self, text_edit, parent=None):
        """
        Initializes a button with an icon and a tooltip. Connects the clicked signal to the clear slot of the output text field.

        :param text_edit (QTextEdit): The output text field to clear.
        :param parent (QWidget, optional): The parent widget for this button. Default is None.
        """
        super().__init__(parent)
        self.setIcon(QIcon(resource_path('clear.png')))
        self.setIconSize(QSize(14, 14))
        self.setToolTip("Clear Output")
        self.clicked.connect(lambda: text_edit.clear())


class Worker(QThread):
    """
    A worker thread for handling the generation of chat responses.
    """
    finished = pyqtSignal(list)
    update_ui = pyqtSignal(list)

    def __init__(self, model, message_history, parent=None):
        """
        Initializes the Worker thread.

        :param model: The language model to use for response generation.
        :param message_history: The history of chat messages.
        :param parent: The parent QObject.
        """
        super().__init__(parent)
        self.model = model
        self.message_history = message_history
        self.output_text = CustomTextEdit()

    def run(self):
        """
        Runs the worker thread.
        """
        try:
            response = g4f.ChatCompletion.create(
                model=self.model,
                messages=self.message_history,
                stream=False
            )
            self.finished.emit(list(response))
            self.update_ui.emit(list(response))
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            self.output_text.write(error_message)
            self.finished.emit([error_message])
            self.update_ui.emit([error_message])


class CreateDatabaseDialog(QDialog):
    """
    A dialog for creating a new SQLite database.
    """
    def __init__(self, folder_path, parent=None):
        """
        Initializes the CreateDatabaseDialog.

        :param folder_path: The folder in which to create the database.
        :param parent: The parent QObject.
        """
        super().__init__(parent)

        self.folder_path = folder_path

        self.setWindowTitle("Create Database")
        self.layout = QVBoxLayout(self)

        self.db_name_input = QLineEdit(self)
        self.db_name_input.setStyleSheet("color: white;")
        self.db_name_input.setPlaceholderText("Enter database name (ex. my_database)")

        self.create_button = QPushButton("Create", self)
        self.create_button.clicked.connect(self.create_database)

        self.layout.addWidget(self.db_name_input)
        self.layout.addWidget(self.create_button)

        self.resize(270, 170)

    def create_database(self):
        """
        Creates a new SQLite database.
        """
        db_input = self.db_name_input.text()
        if not db_input:
            QMessageBox.warning(self, "Error", "Please enter a database name.")
            return

        db_name = f"{db_input}.db"
        database_path = os.path.join(self.folder_path, db_name)

        if not os.path.exists(database_path):
            os.makedirs(self.folder_path, exist_ok=True)

            with sqlite3.connect(database_path) as conn:
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS history
                             (date text, role text, content text, response text)''')

            QMessageBox.information(self, "Database Created", "Database created successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Database already exists. Please choose another name.")


class ChatApp(QWidget):
    """
    The main application window for the chat application.
    """
    def __init__(self):
        """
        Initializes the ChatApp window.
        """
        super().__init__()
        self.current_prompt = ""
        self.message_history = []
        self.conn = None
        self.c = None

        self.output_text = CustomTextEdit()

        self.database_folder = None
        self.database_path = None

        self.setWindowTitle("ChatLanguageModels")
        layout = QVBoxLayout(self)

        self.prompt_input = QTextEdit(self)
        self.prompt_input.setText(self.current_prompt)
        self.prompt_input.setMaximumHeight(100)
        layout.addWidget(self.prompt_input)

        self.model_combo = QComboBox(self)
        self.model_combo.setMaximumHeight(100)
        self.model_combo.addItems(models.keys())
        layout.addWidget(self.model_combo)

        self.submit_button = QPushButton("Submit", self)
        self.submit_button.clicked.connect(self.submit_clicked)
        layout.addWidget(self.submit_button)

        self.output_text = CustomTextEdit()
        self.output_text.setMaximumHeight(700)
        layout.addWidget(self.output_text)

        self.clear_input_button = ClearButton(self.prompt_input, self)
        self.clear_input_button.setGeometry(5, 6, 25, 25)

        self.clear_log_button = ClearLogButton(self.output_text, self)
        self.clear_log_button.setGeometry(5, 208, 25, 25)

        if not self.database_folder:
            self.output_text.write("Please specify the folder and the database before the start!")

        self.worker = Worker(models[self.model_combo.currentText()], self.message_history)
        self.worker.finished.connect(self.update_ui)

        self.long_running_task_timer = QTimer(self)
        self.long_running_task_timer.timeout.connect(self.perform_long_running_task)

        self.select_folder_button = QPushButton("Select Folder", self)
        self.select_folder_button.clicked.connect(self.select_folder_clicked)
        layout.addWidget(self.select_folder_button)

        self.create_database_button = QPushButton("Create Database", self)
        self.create_database_button.clicked.connect(self.create_database_clicked)
        layout.addWidget(self.create_database_button)

        self.select_database_button = QPushButton("Select Database", self)
        self.select_database_button.clicked.connect(self.select_database_clicked)
        layout.addWidget(self.select_database_button)

        self.clear_database_button = QPushButton("Clear Message History", self)
        self.clear_database_button.clicked.connect(self.clear_database_clicked)
        layout.addWidget(self.clear_database_button)

        styles = """
                    QWidget {
                        background-color: #2E3A4F;
                        font-family: Consolas;
                        border-radius: 10px;
                    }
                    
                    QMessagebox {
                        color: #FFFFFF;
                    }

                    QComboBox {
                        background-color: #37485E;
                        border: 3px solid #2E3A4F;
                        padding: 10px;
                        font-size: 14px;
                        color: #E0E0E0;
                        border-radius: 10px;
                    }

                    QComboBox QAbstractItemView {
                        background-color: #37485E;
                        color: #FFFFFF;
                        border: 1px solid #2E3A4F;
                        selection-background-color: #1E2532;
                    }

                    QPushButton {
                        background-color: #1E2532;
                        color: #B0B0B0;
                        border: none;
                        padding: 10px 20px;
                        height: 20px;
                        font-size: 16px;
                        border-radius: 12px;
                    }

                    QPushButton:pressed {
                        background-color: #263042;
                        border: 3px solid #2E3A4F;
                        color: #FFFFFF;
                    }

                    QTextEdit, QTextEdit#output_text {
                        background-color: #37485E;
                        border: 5px solid #2E3A4F;
                        padding: 10px;
                        font-size: 14px;
                        color: #E0E0E0;
                        border-radius: 10px;
                    }
                """

        self.setStyleSheet(styles)
        self.setWindowIcon(QIcon(resource_path('icon2.png')))
        self.set_geometry_centered()

    def update_output_text(self, text):
        self.output_text.insertPlainText(text)
        self.output_text.moveCursor(QTextCursor.MoveOperation.EndOfBlock)
        self.output_text.setReadOnly(True)

    def set_geometry_centered(self):
        """
        Centers the main window on the screen.
        """
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2

        self.setGeometry(x, y, 600, 600)

    def set_tooltips(self):
        """
        Sets tooltips for UI elements.
        """
        self.submit_button.setToolTip("Submit the current prompt for a response.")
        self.select_folder_button.setToolTip("Select the folder for saving databases.")
        self.select_database_button.setToolTip("Select an existing database.\n"
                                               "Used to store a message history.\n"
                                               "Note: You can delete the .db file anytime.")
        self.clear_database_button.setToolTip("Clears message history from the selected database.\n"
                                              "Note: Generating is faster after clearing.")
        self.model_combo.setToolTip("Select the language model for generating responses.")
        self.create_database_button.setToolTip("Create a new database.")

    def select_folder_clicked(self):
        """
        Handles the click event for the "Select Folder" button.
        """
        self.scroll_to_end()

        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        self.database_folder = folder_dialog.getExistingDirectory(self, "Select Folder")

        if not self.database_folder:
            return

        os.makedirs(self.database_folder, exist_ok=True)

        self.output_text.write(f"Selected folder: {self.database_folder}")

    def select_database_clicked(self):
        """
        Handle the click event for the "Select Database" button.
        """
        self.scroll_to_end()

        if not self.database_folder:
            self.output_text.write("Please select a folder first.")
            return

        database_dialog = QFileDialog()
        database_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        database_dialog.setNameFilter("Database files (*.db)")
        selected_database = database_dialog.getOpenFileName(self, "Select Database", self.database_folder,
                                                            "Database files (*.db)")

        if selected_database[0]:
            self.database_path = selected_database[0]

            self.load_database_clicked(self.database_path)

    def create_database_clicked(self):
        """
        Handles the click event for the "Create Database" button.
        """
        self.scroll_to_end()

        if not self.database_folder:
            self.output_text.write("Please select a folder first.")
            return

        create_db_dialog = CreateDatabaseDialog(self.database_folder, self)
        result = create_db_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            db_name_input = create_db_dialog.db_name_input.text()
            if not db_name_input:
                self.output_text.write("Please enter a database name.")
                return

            db_name = f"{db_name_input}.db"
            self.database_path = os.path.join(self.database_folder, db_name)
            self.load_database_clicked(self.database_path)

    def load_database_clicked(self, database_path):
        """
        Loads a database from the specified path.

        :param database_path: The path to the database file.
        """
        self.scroll_to_end()

        self.database_path = database_path
        with sqlite3.connect(self.database_path) as self.conn:
            self.c = self.conn.cursor()
            self.c.execute("CREATE TABLE IF NOT EXISTS history (date text, role text, content text, response text)")

            self.c.execute("SELECT * FROM history")
            self.message_history = [{"date": row[0], "role": row[1], "content": row[2], "response": row[3]} for row in
                                    self.c.fetchall()]

        self.output_text.write(f"Using database: {self.database_path}")

    def clear_database_clicked(self):
        """
        Clears the message history from the selected database.
        """
        self.scroll_to_end()

        if not self.database_folder:
            self.output_text.write("Please select a folder first.")
            return

        database_dialog = QFileDialog()
        database_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        database_dialog.setNameFilter("Database files (*.db)")
        selected_database = database_dialog.getOpenFileName(self, "Select Database", self.database_folder,
                                                            "Database files (*.db)")

        if not selected_database[0]:
            self.output_text.write("No database selected.")
            return

        self.database_path = selected_database[0]

        confirmation = QMessageBox.question(self, "Clear Database",
                                            f"Are you sure you want to clear the database at\n{self.database_path}?",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmation == QMessageBox.StandardButton.Yes:
            with sqlite3.connect(self.database_path) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM history")
                conn.commit()

                self.output_text.write("Database cleared.")
        else:
            self.output_text.write("Database not cleared.")

    def submit_clicked(self):
        """
        Handles the click event for the "Submit" button.
        """
        if not self.database_folder:
            self.output_text.write("Please select a folder first.")
            return
        if not self.database_path:
            self.output_text.write("Please select a database first.")
            return
        self.output_text.write('Prompt is submitted. Wait for response generation.')
        self.worker.model = models[self.model_combo.currentText()]
        self.current_prompt = self.prompt_input.toPlainText()

        current_time = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')

        new_message = {"date": current_time, "role": "helpful assistant", "content": self.current_prompt, "response": " "}
        self.message_history.append(new_message)

        self.long_running_task_timer.start(0)

    def generate_response(self):
        """
        Generates a response using the selected language model.
        """
        self.worker = Worker(models[self.model_combo.currentText()], self.message_history)
        self.worker.finished.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, response):
        """
        Updates the UI with the generated response.

        :param response: The list of response messages.
        """
        self.scroll_to_end()

        overall_message = ""
        for message in response:
            overall_message += message

        self.output_text.write(overall_message)

        current_time = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        message_info = {"date": current_time, "role": "helpful assistant",
                        "content": self.current_prompt, "response": overall_message}
        self.message_history.append(message_info)

        message_info['response'] = overall_message
        self.c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (message_info['date'], message_info['role'],
                                                                   message_info['content'], message_info['response']))
        self.conn.commit()

        self.scroll_to_end()

    def scroll_to_end(self):
        """
        Scrolls to the end of the QTextEdit widget.
        """
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)

    def perform_long_running_task(self):
        """
        Performs the long-running task of generating a response.
        """
        self.long_running_task_timer.stop()
        self.generate_response()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    chat_app = ChatApp()
    chat_app.set_tooltips()
    chat_app.show()
    sys.exit(app.exec())
