# adhahi-auto-register — GUI Fork 🇩🇿🐑

> A graphical desktop interface built on top of [ATOUIYakoub/adhahi-auto-register](https://github.com/ATOUIYakoub/adhahi-auto-register).  
> All credit for the original automation logic goes to the upstream project.

https://github.com/user-attachments/assets/d5825e3b-5fe1-4fc6-92f8-dedf895cac03

---

## What's different from the original

The original script requires you to manually edit your credentials directly in the `.py` file before every run. This fork wraps the same logic in a full desktop GUI so that:

- Credentials and wilaya selection are entered through a form — no code editing needed
- Config is saved automatically to `adhahi_config.json` and reloaded on next launch
- The bot runs continuously 24/7 until you click Stop — it does not exit after finding one wilaya
- Multiple wilayas can open simultaneously and each gets its own browser session
- A live colour-coded log panel shows every poll and every action in real time
- CAPTCHA input is handled through a GUI popup instead of the terminal
- Telegram alerts work the same as the original
- The project can be compiled to a standalone `.exe` using the included `build.bat`

---

## Files

| File | Purpose |
|------|---------|
| `adhahi_gui.py` | Main application — run this with Python or compile it |
| `build.bat` | Compiles `adhahi_gui.py` into a Windows `.exe` using PyInstaller |
| `icon.ico` | *(optional)* App icon — place in the same folder before building |

---

## Requirements

- **Python 3.10+**
- **Google Chrome** installed on the machine running the bot
- Dependencies:

```
pip install selenium webdriver-manager
```

> ChromeDriver is downloaded automatically at runtime by `webdriver-manager`. You do not need to install it manually.

---

## Running with Python

```bash
pip install selenium webdriver-manager
python adhahi_gui.py
```

### How to use

1. Fill in your credentials in the **left panel** (NIN, CNI, phone, password)
2. Select your target wilayas from the checklist
3. Optionally add your Telegram Bot Token and Chat ID for phone alerts
4. Click **▶ Start Monitoring**

The bot will poll the adhahi.dz API every N seconds (configurable). The moment a target wilaya opens, Chrome launches automatically, fills the form, and pauses at the CAPTCHA — a popup appears asking you to type what you see in the Chrome window. After submitting, you enter the SMS OTP directly in the browser.

---

## Building the EXE

> Requires Python and pip in your system PATH.

1. Place `adhahi_gui.py`, `build.bat`, and optionally `icon.ico` in the same folder
2. Double-click `build.bat`
3. The script will install PyInstaller, clean any previous build, and compile the project
4. Output is in `dist\adhahi_bot\adhahi_bot.exe`

**Important:** always distribute the entire `dist\adhahi_bot\` folder, not just the `.exe` file. PyInstaller places required DLLs and data files next to the executable.

On first launch the exe will download ChromeDriver automatically — an internet connection is required.

### Custom icon

Place a file named `icon.ico` in the same folder as `build.bat` before building. The script detects it automatically. If it is missing the exe will use the default Python icon. You can convert any PNG to ICO at [icoconvert.com](https://icoconvert.com).

---

## ⚠️ Limitations (inherited from original)

- **Geo-blocking:** adhahi.dz blocks requests from outside Algeria. Run this on a PC connected to an Algerian network. Cloud providers and foreign VPNs will get a timeout or 403.
- **CAPTCHA is manual:** There is no auto-solve. When Chrome opens and fills the form, it will pause and show a popup asking you to type the CAPTCHA characters visible in the browser window.
- **OTP is manual:** After submitting, enter the 6-digit SMS code directly in the Chrome window.
- **Poll rate:** Do not set the interval below 2 seconds or your IP may get temporarily blocked by the API.

---

## Telegram setup (optional)

1. Open Telegram and message `@BotFather` → `/newbot` → follow the steps → copy the **Bot Token**
2. Message `@userinfobot` to get your **Chat ID**
3. Paste both into the Telegram section of the GUI
4. Click **🔔 Test** to verify it works before starting the bot

You will receive alerts when a wilaya opens, when the CAPTCHA needs solving, when the OTP step is reached, and when registration is submitted.

---

## Credits

Original project and automation logic by [ATOUIYakoub](https://github.com/ATOUIYakoub/adhahi-auto-register).  
GUI wrapper, EXE build pipeline, and session management improvements by [harrysof](https://github.com/harrysof).

---

## Disclaimer

Unofficial tool. Use responsibly and at your own risk. Not affiliated with adhahi.dz or any government entity.
