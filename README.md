# 🧠 Jarvis V2 --- AI Desktop Assistant

### *A next-generation intelligent Windows assistant with voice, automation, and a premium UI experience*

------------------------------------------------------------------------

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6-green?logo=qt)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-Open--Source-orange)

------------------------------------------------------------------------

## 🚀 Overview

**Jarvis V2** is a powerful, voice-enabled AI desktop assistant built
for Windows.\
It combines intelligent command routing, real-time system automation,
and a futuristic animated interface to deliver a seamless human-computer
interaction experience.

------------------------------------------------------------------------

## ✨ Features

### 🧠 AI + Command System

-   Intelligent command routing pipeline\
-   Multi-layer processing:
    -   Hard rules
    -   Dataset matching
    -   Alias matching
    -   AI fallback
-   Bangla 🇧🇩 + English 🇺🇸 language support

------------------------------------------------------------------------

### 🎙️ Voice System

-   Speech-to-Text (STT)
-   Text-to-Speech (TTS)
-   Voice command execution
-   State-based assistant behavior:
    -   🟢 Listening\
    -   🟡 Thinking\
    -   🔵 Speaking

------------------------------------------------------------------------

### ⚙️ System Automation

  Feature             Description
  ------------------- ----------------------------------
  🔊 Volume Control   Increase, decrease, mute, unmute
  📸 Screenshot       Capture screen instantly
  🌐 Web Actions      Open YouTube, browser
  📁 File Access      Open Downloads, Desktop
  🔍 Web Search       Smart query execution
  🌦️ Weather          Quick weather lookup

------------------------------------------------------------------------

### 🎨 UI & Experience

-   🟣 Animated **Jarvis Orb** (state-driven)
-   📊 Voice waveform visualizer
-   🌌 Dynamic particle background
-   🎛️ Floating action buttons (real commands)
-   📦 Expandable UI cards
-   📜 Command timeline/history
-   🪟 Movable UI panels
-   🎯 Animated sidebar interactions

------------------------------------------------------------------------

## 🏗️ Architecture

User Input → AssistantController → CommandRouter → RouteHandler →
Actions → ResponseBuilder → UI + Voice Output

------------------------------------------------------------------------

## 🖥️ UI Highlights

-   Futuristic assistant interface with real-time feedback\
-   Visual voice interaction with waveform animation\
-   State-aware assistant orb (Listening → Thinking → Speaking)\
-   Smooth transitions, hover effects, and responsive panels

------------------------------------------------------------------------

## 📦 Installation

git clone https://github.com/abdurrahman422/jarvis-v2.git\
cd jarvis-v2

python -m venv .venv\
..venv`\Scripts`{=tex}`\activate  `{=tex}

pip install -r requirements.txt

------------------------------------------------------------------------

## ▶️ Run

python -m app.main

------------------------------------------------------------------------

## 💬 Example Commands

"Open YouTube"\
"Volume komao"\
"Take screenshot"\
"Open Downloads folder"\
"Search weather in Dhaka"\
"Mute system"

------------------------------------------------------------------------

## ⚠️ Notes & Requirements

-   AI models are **not included** in the repository\
-   Place models inside: app/models/\
-   Some features require:
    -   pywin32
    -   pyautogui
    -   requests

------------------------------------------------------------------------

## 🧬 Version Info

V1 → Basic system\
V2 → Animated UI + Clean architecture

------------------------------------------------------------------------

## 🔮 Future Plans

-   Advanced AI integration\
-   Improved offline capabilities\
-   Better Bangla voice support\
-   Plugin system

------------------------------------------------------------------------

## 👨‍💻 Author

**Abdur Rahman**

------------------------------------------------------------------------

## 💡 Support

⭐ Star the repo\
🍴 Fork it\
🐛 Report issues

------------------------------------------------------------------------

## 🧾 Final Note

"Jarvis V2 is not just an assistant --- it's your personal AI operating
layer."
