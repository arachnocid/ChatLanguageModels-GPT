# ChatLanguageModels-GPT4-for-free
ChatLanguageModels is a PyQt6-based desktop application that utilizes the g4f library to interact with various language models (e.g., GPT-4 and GPT-3.5 Turbo). Additionally, it supports the creation and management of SQLite databases to store chat history.

<img src="https://github.com/arachnocid/ChatLanguageModels-GPT4-for-free/blob/d7cd31a0bfd978c100396bcd9d0a0d26f345a1ea/ChatLanguageModels.png" height="200">

## Features
- **Language Models:** Choose from a variety of language models.
- **Database Management:** Select, create, and clear databases to store the chat message history.
- **User-Friendly Interface:** Easy-to-use graphical interface for interacting with language models.

### Prerequisites
- Python 3.x
- PyQt6
- g4f

## Getting Started
**Using the Executable (Windows):**
1. Download the latest release from the "Releases" section.
2. Double-click the executable file (ChatLanguageModels.exe) to run the program.
3. Select the prefered folder to store database files.
4. Create new or select the existing database.
5. Type your prompt.
6. When finished, press the "submit" button. The program will begin searching for currently avaliable model and generate response.
7. If the response does not appear, but the prompt was submitted, don't press the "submit" button again, it might take some time.

**Running from Source Code:**
1. Clone this repository to your local machine.
   ```bash
   git clone https://github.com/arachnocid/ChatLanguageModels-GPT4-for-free.git
2. Install the required dependencies (see requirements.txt)
   ```bash
   pip install -r requirements.txt
3. Navigate to the project directory and find "ChatLanguageModels.py"
4. Run the script.
5. Select the prefered folder to store database files.
6. Create new or select the existing database.
7. Type your prompt.
8. When finished, press the "submit" button. The program will begin searching for currently avaliable model and generate response.
9. If the response does not appear, but the prompt was submitted, don't press the "submit" button again, it might take some time.

## .gitignore
This repository uses the standard Python .gitignore file to exclude temporary files and Python virtual environments from version control.

## License
This project is licensed under the MIT License.

## Author
Arachnocid
