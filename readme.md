# 🤖 Smart Customer Support Ticketing System (RAG-based)

An intelligent support tool that uses Retrieval-Augmented Generation (RAG) to understand customer queries, categorize them, search past tickets and documentation, and generate smart, helpful responses.

## 🧠 Models Used

| Purpose             | Model                                          |
| ------------------- | ---------------------------------------------- |
| Embeddings          | `all-MiniLM-L6-v2` via `sentence-transformers` |
| LLM (for responses) | Local model via LM Studio (e.g., google/gemma) |

---

## 🛠️ Setup Instructions

### 1. Clone and setup environment

```bash
git clone https://github.com/your-username/ticketing-system.git
cd ticketing-system
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate (Windows)

pip install -r requirements.txt #install requirements

streamlit run app.py # run app

```
