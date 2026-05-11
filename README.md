# 🎮 CodeSynapse: AI Career Architect

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)
![Gradio](https://img.shields.io/badge/Frontend-Gradio-orange?style=for-the-badge&logo=gradio&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![HuggingFace](https://img.shields.io/badge/Deployment-Hugging%20Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)

**Live Demo:** [Click Here to Launch App](https://huggingface.co/spaces/SwarangiK-21/CodeSynapse)

CodeSynapse is a futuristic, AI-powered analytics dashboard designed for Computer Science students. It aggregates coding performance data from multiple platforms, visualizes skill competencies, and provides an AI Career Coach to generate personalized study roadmaps and career advice.

---

## 🚀 Key Features

### 1. 🔗 Multi-Platform Identity Uplink
- **Real-time Sync:** Fetches live user profiles from **GitHub**, **LeetCode**, and **GeeksForGeeks**.
- **Data Aggregation:** Consolidates repository counts, problem-solving stats, rankings, and coding scores into a single unified view.
- **HackerRank:** Integration coming in a future update.

### 2. 📊 Competency Radar Matrix
- **Visual Analytics:** Uses **Plotly Express** to generate interactive Cyberpunk-styled radar charts.
- **Skill Scoring:** Normalizes data from different platforms to calculate a "Competency Score" (0–100) per platform.

### 3. 🤖 AI Nexus Coach
- **Powered by Google Gemini Flash:** A built-in AI chatbot that is contextually aware of your actual fetched stats.
- **Career Advice:** Ask for project ideas, DSA roadmaps, or study plans tailored to your weak areas.
- **Self-Healing Logic:** Automatically falls back across 4 Gemini model variants to ensure the AI always responds, even during quota limits.

### 4. 📄 Instant Career Report
- **One-Click PDF Download:** Generates a clean, printable career summary from your synced stats.
- **ReportLab Integration:** Produces a structured PDF report on the fly.

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Frontend | Gradio (Custom Cyberpunk Dark/Neon Theme) |
| Backend | Python 3.11, AsyncIO |
| AI Engine | Google Gemini Flash API |
| Data Visualization | Plotly Express, Pandas |
| Data Fetching | AIOHTTP (GitHub, LeetCode), Playwright (GFG) |
| PDF Generation | ReportLab |
| Database | SQLite3 |
| Deployment | Hugging Face Spaces |

---

## 🗂️ Project Structure

```
CodeSynapse/
│
├── app.py                  # Main UI — Gradio interface & event wiring
├── logic/
│   ├── fetchers.py         # Async platform data fetchers
│   ├── ai_coach.py         # Gemini AI integration with fallback chain
│   └── database.py         # SQLite — profile & chat history storage
├── requirements.txt
└── README.md
```

---

## ⚙️ How It Works

1. Enter your usernames for GitHub, LeetCode, and GeeksForGeeks.
2. Click **⚡ INITIALIZE SYNC** — all platforms are fetched in parallel using `asyncio.gather`.
3. View your **Competency Radar** chart and full stats breakdown.
4. Switch to the **AI Nexus** tab and ask the coach anything — it already knows your stats.
5. Download your **PDF Career Report** with one click.

---

## 🔧 Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/your-username/CodeSynapse.git
cd CodeSynapse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser
playwright install chromium

# 4. Add your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# 5. Run the app
python app.py
```

App will be live at `http://localhost:7860`

---

## 🗺️ Roadmap

- [x] GitHub live stats
- [x] LeetCode live stats (GraphQL)
- [x] GeeksForGeeks scraping (Playwright)
- [x] AI Coach with Gemini fallback chain
- [x] PDF report generation
- [x] SQLite chat & profile history
- [ ] HackerRank live integration
- [ ] User authentication
- [ ] Styled PDF with charts embedded
- [ ] Weekly progress tracking & email digest

---

*Built with 💻 and ☕ by Swarangi Kothawade*
