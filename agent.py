import os
import sys
import json
import time
import threading
import subprocess
import requests
import pyautogui

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pytesseract
    from PIL import Image

    # Explicitly set path for standard Windows Tesseract installation
    if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pytesseract = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Ollama API configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
ACTIVE_MODEL = "local-engineer"  # <-- Updated to use your custom personality core!
AVAILABLE_MODELS = [
    "local-engineer",
    "huihui_ai/qwen2.5-abliterate:14b-instruct",
    "dolphin3:8b"
]

monitoring_active = False
last_window_title = ""


def log_activity(entry):
    """Logs agent interactions and telemetry to a local file."""
    try:
        with open("agent_activity_log.txt", "a", encoding="utf-8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {entry}\n")
    except Exception:
        pass


def get_active_window_info():
    """Retrieves title of the active window."""
    if gw is None:
        return "Unknown"
    try:
        active_window = gw.getActiveWindow()
        return active_window.title if active_window else "Unknown"
    except Exception:
        return "Unknown"


def check_git_status():
    """Checks local Git repository status."""
    try:
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return f"[Git Status]:\n{result.stdout.strip()}"
        return "[Git Status]: Clean or not a git repo."
    except Exception:
        return "[Git Status]: Unavailable."


def perform_ocr_on_screen():
    """Scans text from current screen capture via Tesseract."""
    if not pytesseract:
        return "Tesseract OCR engine not installed or configured."
    try:
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)
        cleaned = " ".join(text.split())
        return cleaned[:1500] if cleaned else "No text detected on screen."
    except Exception as e:
        return f"OCR Error: {e}"


def ask_local_agent(prompt_text):
    """Packages telemetry, desktop state, clipboard, and prompts for local Ollama."""
    window_title = get_active_window_info()
    width, height = pyautogui.size()
    x, y = pyautogui.position()

    git_info = check_git_status()

    clipboard_data = ""
    if pyperclip:
        try:
            clipboard_data = pyperclip.paste()
            if len(clipboard_data) > 800:
                clipboard_data = clipboard_data[:800] + "... [truncated]"
        except Exception:
            pass

    ocr_text = perform_ocr_on_screen()

    context = (f"[Telemetry] Window: '{window_title}' | Screen: {width}x{height} | Mouse: X={x}, Y={y}\n"
               f"{git_info}\n"
               f"[Screen OCR Text Preview]: {ocr_text[:300]}...\n"
               f"[Clipboard Content]: {clipboard_data if clipboard_data else 'None'}")

    full_prompt = f"{context}\n\nUser Request: {prompt_text}"

    payload = {
        "model": ACTIVE_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.2}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        output = response.json().get('response', '')
        log_activity(f"Model: {ACTIVE_MODEL} | Prompt: {prompt_text}")
        return output
    except Exception as e:
        return f"AI Co-pilot connection error: {e}"


def execute_and_self_correct(code_text, max_retries=2):
    """Executes Python code and automatically feeds tracebacks back to AI if it fails."""
    filename = "temp_execution.py"
    current_code = code_text

    for attempt in range(max_retries + 1):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(current_code)

            print(f"\n[+] Executing code (Attempt {attempt + 1}/{max_retries + 1})...")
            result = subprocess.run([sys.executable, filename], capture_output=True, text=True, timeout=30)

            if result.stdout:
                print("--- Output ---\n", result.stdout)

            if result.returncode != 0:
                error_output = result.stderr
                print("--- Execution Error ---\n", error_output)

                if attempt < max_retries:
                    print("[*] Self-Correction: Sending traceback back to model for a fix...")
                    fix_prompt = f"Fix this Python code based on the traceback error below. Return ONLY corrected code in ```python blocks:\n\nCODE:\n{current_code}\n\nERROR:\n{error_output}"

                    ai_fix_response = ask_local_agent(fix_prompt)
                    try:
                        if "```python" in ai_fix_response:
                            current_code = ai_fix_response.split("```python")[1].split("```")[0].strip()
                        else:
                            current_code = ai_fix_response.split("```")[1].split("```")[0].strip()
                        continue
                    except Exception:
                        print("[!] Failed to parse fix from AI response.")
                        break
                else:
                    print("[!] Max self-correction retries reached.")
            else:
                print("[+] Script executed successfully!")
                break
        except Exception as e:
            print(f"[!] Execution exception: {e}")
            break


def background_watcher():
    """Background thread monitoring active windows for error states and high system load."""
    global monitoring_active, last_window_title
    print("\n[Background Co-Pilot] Started background telemetry & resource guardian...")

    while monitoring_active:
        if psutil:
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_usage = psutil.virtual_memory().percent
            if cpu_usage > 90 or mem_usage > 90:
                print(f"\n[!] Resource Guardian Alert: High system load! CPU: {cpu_usage}%, RAM: {mem_usage}%")

        current_window = get_active_window_info()
        error_keywords = ["error", "exception", "crash", "failed", "debug", "x64dbg"]
        if any(kw in current_window.lower() for kw in error_keywords) and current_window != last_window_title:
            print(f"\n[!] Co-Pilot Alert: Potential debugging state in window: '{current_window}'")
            suggestion = ask_local_agent(f"User focused on error window '{current_window}'. Provide brief fix tip.")
            print(f"\n--- Suggestion ---\n{suggestion}\n--------------------")
            print("[LocalEngineer] >>> ", end="", flush=True)

        last_window_title = current_window
        time.sleep(12)


def main_loop():
    global monitoring_active, ACTIVE_MODEL
    print("==================================================")
    print("   Local Engineer & OS Co-Pilot Agent (v6.1)      ")
    print("==================================================")
    print(f"Connected Model : {ACTIVE_MODEL}")
    print("--------------------------------------------------")
    print("Commands: 'clip', 'ocr', 'model', 'startwatch', 'stopwatch', 'exit'\n")

    while True:
        try:
            user_input = input("\n[LocalEngineer] >>> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                monitoring_active = False
                print("Goodbye!")
                break
            elif user_input.lower() == "startwatch":
                if not monitoring_active:
                    monitoring_active = True
                    threading.Thread(target=background_watcher, daemon=True).start()
                    print("[+] Background watcher active.")
                continue
            elif user_input.lower() == "stopwatch":
                monitoring_active = False
                print("[-] Background watcher paused.")
                continue
            elif user_input.lower() == "clip":
                if pyperclip:
                    user_input = f"Analyze this clipboard content:\n\n{pyperclip.paste()}"
                else:
                    print("[!] pyperclip not available.")
                    continue
            elif user_input.lower() == "ocr":
                print("[*] Scanning screen text via OCR...")
                ocr_result = perform_ocr_on_screen()
                print(f"\n--- Screen OCR Result ---\n{ocr_result}\n-------------------------")
                continue
            elif user_input.lower() == "model":
                print("\nAvailable Models:")
                for i, m in enumerate(AVAILABLE_MODELS):
                    marker = " (active)" if m == ACTIVE_MODEL else ""
                    print(f"  [{i + 1}] {m}{marker}")
                choice = input("Select model number: ").strip()
                if choice in ["1", "2", "3"]:
                    ACTIVE_MODEL = AVAILABLE_MODELS[int(choice) - 1]
                    print(f"[+] Switched model to: {ACTIVE_MODEL}")
                continue

            agent_output = ask_local_agent(user_input)
            print("\n--- Agent Response ---\n", agent_output, "\n----------------------")

            if "```" in agent_output:
                if input("[?] Execute & self-correct Python code? (y/n): ").strip().lower() == 'y':
                    try:
                        if "```python" in agent_output:
                            code_block = agent_output.split("```python")[1].split("```")[0].strip()
                        else:
                            code_block = agent_output.split("```")[1].split("```")[0].strip()
                        execute_and_self_correct(code_block)
                    except Exception as e:
                        print(f"[!] Parsing error: {e}")
        except KeyboardInterrupt:
            monitoring_active = False
            break


if __name__ == "__main__":
    main_loop()