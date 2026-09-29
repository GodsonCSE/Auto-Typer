# 🚀 Universal Auto Typer

A fast and customizable auto-typing tool with a modern web interface. Paste text or code, configure the typing speed, and automatically type it character-by-character.

🌐 **Live Website:** https://auto-typer-7cav.onrender.com

---

## ✨ Features

* 🖥️ Modern and responsive web interface
* ⌨️ Automatic character-by-character typing
* ⚡ Multiple typing speeds
* ▶️ Start / Stop controls
* 🧹 Clear text functionality
* 💻 Browser typing mode
* 🪟 Windows local system typing mode
* 🔥 Supports programming code and normal text
* 📋 Easy copy/paste workflow
* 🎯 Useful for coding practice, demonstrations, testing, and repetitive typing
* 🌐 Can be accessed through a public URL

---

## 🌐 Live Demo

Try the application directly in your browser:

**https://auto-typer-7cav.onrender.com**

The web application can be accessed without installing Python or the source code.

---

## 🖥️ Two Typing Modes

### 1. 🌐 Browser Mode

Browser Mode runs directly inside the web browser.

```text
Browser
   ↓
Universal Auto Typer
   ↓
Browser text input
```

This mode is useful when you only need typing functionality inside the browser.

---

### 2. 🪟 Local System Mode

Local System Mode is designed for Windows.

The local executable runs on the user's computer and can interact with the system keyboard.

```text
UniversalAutoTyper.exe
        ↓
Windows Keyboard
        ↓
Active Application
```

This allows the user to type into applications outside the browser.

> ⚠️ The Render server itself cannot directly control a visitor's physical keyboard. Local System Mode therefore requires the Windows application to run on that computer.

---

## 🛠️ Technologies Used

### Backend

* Python
* Flask

### Frontend

* HTML5
* CSS3
* JavaScript

### Desktop Automation

* PyAutoGUI
* Keyboard automation

### Deployment

* Render
* GitHub

### Executable

* PyInstaller

---

## 📂 Project Structure

```text
Universal-Auto-Typer/
│
├── local_app.py
├── requirements.txt
├── build.bat
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
├── dist/
│   └── UniversalAutoTyper.exe
│
└── README.md
```

> The exact structure may vary depending on the current version of the project.

---

## 💻 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/GodsonCSE/Universal-Auto-Typer.git
```

```bash
cd Universal-Auto-Typer
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the application

```bash
python local_app.py
```

Then open:

```text
http://127.0.0.1:5000
```

---

# 📦 Create the Windows EXE

The project includes a `build.bat` file for creating the executable.

Run:

```bat
build.bat
```

PyInstaller creates:

```text
dist/
└── UniversalAutoTyper.exe
```

The executable is packaged as a single file using PyInstaller.

---

## 🪟 Using the Windows EXE

1. Build the application.
2. Open the `dist` folder.
3. Run:

```text
UniversalAutoTyper.exe
```

4. Open the application.
5. Paste the text or code you want to type.
6. Select the desired typing speed.
7. Start the typing process.
8. Stop the process whenever required.

---

## ⌨️ Keyboard Controls

| Shortcut    | Action       |
| ----------- | ------------ |
| `Shift + Z` | Start typing |
| `Shift + X` | Stop typing  |

These shortcuts are intended for the local Windows application.

---

## 🎯 Example Use Cases

Universal Auto Typer can be useful for:

* 💻 Coding demonstrations
* 🧑‍💻 Programming practice
* 🎥 Screen-recording demonstrations
* 🧪 Testing text-input interfaces
* 📝 Repetitive text entry
* 🎓 Educational demonstrations
* ⚙️ Automation experiments

---

## ⚙️ How It Works

The application takes the text entered by the user and processes it character by character.

```text
User enters text
       ↓
Select typing speed
       ↓
Press Start
       ↓
Characters are processed
       ↓
Keyboard automation
       ↓
Target application receives the input
```

---

## 🌐 Deployment

The web version is deployed using Render.

Live application:

**https://auto-typer-7cav.onrender.com**

A typical deployment flow is:

```text
GitHub Repository
       ↓
Render
       ↓
Flask Application
       ↓
Public URL
```

---

## 🔐 Privacy

Universal Auto Typer is designed as a typing/automation utility.

When using the public web application, avoid entering:

* Passwords
* API keys
* Banking information
* Private credentials
* Other sensitive information

Only use the application with content you are authorized to automate.

---

## ⚠️ Important Notes

### Windows permissions

Some applications may restrict automated keyboard input. Running the application with appropriate permissions may be necessary depending on the target application.

### Antivirus warnings

A self-built PyInstaller executable can sometimes trigger Windows SmartScreen or antivirus warnings because the executable is not digitally signed.

Only run executables from a source you trust.

### Render limitations

The public Render server cannot directly access or control the physical keyboard of the person visiting the website.

For system-wide typing on Windows, the local executable must run on the user's computer.

---

## 🧑‍💻 Development

To modify the project:

```bash
git clone https://github.com/GodsonCSE/Universal-Auto-Typer.git
cd Universal-Auto-Typer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
python local_app.py
```

After making changes:

```bash
git add .
git commit -m "Update Universal Auto Typer"
git push
```

If the GitHub repository is connected to Render, the web application can be redeployed from the updated repository.

---

## 🚀 Future Improvements

Possible future features:

* 🔗 Connect the public website with the Windows local agent
* 🔐 Secure agent authentication
* 📡 WebSocket communication
* 📊 Typing statistics
* 💾 Saved typing presets
* 🎨 More customization options
* 🌙 Dark/light themes
* ⏱️ Typing delay controls
* 📥 Downloadable Windows installer

---

## 👨‍💻 Author

**Godson Suresh**

Built as a Python/Flask automation project with a web interface and Windows desktop functionality.

---

## ⭐ Support

If you find the project useful, consider giving the repository a ⭐ on GitHub.


