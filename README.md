# RIVA ChatGPT Docs
 [RIVA ChatGPT Docs](RIVACGPT.md)

---
# Hello World Web Application

A simple Python web application that displays "Hello, World!" in your web browser using Flask.

## What is this project?

This is a beginner-friendly web application built with Python and Flask. When you run it, you can open your web browser and see a nicely formatted "Hello, World!" message. It's perfect for learning the basics of web development with Python!

## Prerequisites

Before you start, make sure you have the following installed on your computer:

- **Python 3.7 or higher** - You can download it from [python.org](https://python.org)
  - To check if Python is installed, open your terminal/command prompt and type: `python --version`
  - If you see a version number like "Python 3.x.x", you're good to go!

## Project Structure

```
cop002/
├── app.py              # Main application file
├── templates/          # HTML template folder
│   └── index.html     # The web page template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Installation Instructions

### Step 1: Download the Project
If you haven't already, download or clone this project to your computer.

### Step 2: Open Terminal/Command Prompt
- **Windows**: Press `Win + R`, type `cmd`, and press Enter
- **Mac**: Press `Cmd + Space`, type `terminal`, and press Enter
- **Linux**: Press `Ctrl + Alt + T`

### Step 3: Navigate to the Project Folder
```bash
cd /path/to/cop002
```
Replace `/path/to/cop002` with the actual path where you downloaded the project.

### Step 4: Create a Virtual Environment (Recommended)
A virtual environment keeps your project dependencies separate from other Python projects.

```bash
# Create virtual environment
python -m venv hello_world_env

# Activate virtual environment
# On Windows:
hello_world_env\Scripts\activate

# On Mac/Linux:
source hello_world_env/bin/activate
```

You'll know it's working when you see `(hello_world_env)` at the beginning of your command prompt.

### Step 5: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs Flask, which is the web framework we're using.

## How to Run the Application

### Step 1: Start the Application
Make sure you're in the project folder and your virtual environment is activated, then run:

```bash
python app.py
```

### Step 2: Open Your Web Browser
You should see output like this:
```
 * Running on http://localhost:5001
 * Debug mode: on
```

### Step 3: View the Application
Open your web browser and go to: **http://localhost:5001**

You should see a beautiful "Hello, World!" message displayed on your screen!

## Stopping the Application

To stop the application:
1. Go back to your terminal/command prompt
2. Press `Ctrl + C` (on both Windows and Mac/Linux)

## Troubleshooting

### Problem: "python: command not found"
**Solution**: Python isn't installed or not in your PATH. Download Python from [python.org](https://python.org) and make sure to check "Add to PATH" during installation.

### Problem: "No module named flask"
**Solution**: Flask isn't installed. Make sure you activated your virtual environment and ran `pip install -r requirements.txt`.

### Problem: "Port 5001 is already in use"
**Solution**: Another application is using port 5001. Either:
- Stop the other application using port 5001, or
- Change the port in `app.py` by modifying the line `app.run(debug=True, host='localhost', port=5001)` to use a different port like `port=5002`

### Problem: Browser shows "This site can't be reached"
**Solution**: 
- Make sure the application is still running in your terminal
- Check that you're using the correct URL: `http://localhost:5001`
- Try `http://127.0.0.1:5001` instead

## What's Next?

Now that you have a working web application, you can:
- Modify the message in `templates/index.html`
- Change the styling by editing the CSS in the HTML file
- Add more pages by creating new routes in `app.py`
- Learn more about Flask at [flask.palletsprojects.com](https://flask.palletsprojects.com)

## Need Help?

If you're stuck, double-check that you followed each step exactly as written. Programming can be tricky at first, but you've got this! 🚀

---

**Congratulations!** You've successfully set up and run your first Python web application!