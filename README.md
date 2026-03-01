# 📘 notebooklm-rest-api

> A REST API wrapper for Google NotebookLM powered by `notebooklm-py`

`notebooklm-rest-api` exposes the functionality of
[`teng-lin/notebooklm-py`](https://github.com/teng-lin/notebooklm-py)
as a clean, production-ready REST API service.

It allows you to manage Notebooks, add sources, perform Q&A, generate artifacts, and download outputs via HTTP.

---

## 🚀 Features

### 📂 Notebook Management

* Create notebook
* List notebooks
* Get notebook details
* Rename notebook
* Delete notebook
* Get summary
* Get description

### 📄 Source Management

* Add URL source
* Add YouTube source
* Add raw text
* Upload file
* Get full text
* Get source guide
* Delete source

### 💬 Chat API

* Ask questions based on notebook context

### 🎨 Artifact Generation

* Audio
* Video
* Report
* Quiz
* Flashcards
* Slide deck
* Infographic
* Data table
* Mind map
* Task polling support
* File download support

### 🔐 Optional API Key Protection

---

## 🧱 Architecture

```
Client (REST)
    ↓
FastAPI
    ↓
notebooklm-py
    ↓
NotebookLM (Web API)
```

---

## 📦 Requirements

* Python 3.10+
* NotebookLM account
* First-time login using `notebooklm login`

---

## ⚙️ Installation

### 1️⃣ Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Authenticate (one-time setup)

```bash
notebooklm login
```

By default, authentication is stored at:

```
~/.notebooklm/storage_state.json
```

You can override it with:

```bash
export NOTEBOOKLM_STORAGE_PATH=/path/to/storage_state.json
```

---

## ▶️ Run Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Swagger UI:

```
http://localhost:8000/docs
```

---

## 🔐 Optional API Key Protection

Set API key:

```bash
export NOTEBOOKLM_REST_API_KEY=your-secret-key
```

Send header:

```
X-API-Key: your-secret-key
```

---

## 📚 API Examples

### List Notebooks

```bash
GET /v1/notebooks
```

---

### Create Notebook

```bash
POST /v1/notebooks
{
  "title": "My Research"
}
```

---

### Add URL Source

```bash
POST /v1/notebooks/{notebook_id}/sources/url
{
  "url": "https://example.com",
  "wait": true
}
```

---

### Ask Question

```bash
POST /v1/notebooks/{notebook_id}/chat/ask
{
  "question": "Summarize the key insights"
}
```

---

### Generate Quiz

```bash
POST /v1/notebooks/{notebook_id}/artifacts/generate
{
  "type": "quiz",
  "options": {}
}
```

---

### Poll Task

```bash
GET /v1/notebooks/{notebook_id}/artifacts/tasks/{task_id}
```

---

### Download Artifact

```bash
GET /v1/notebooks/{notebook_id}/artifacts/download?type=quiz&output_format=json
```

---

## 🌍 Environment Variables

| Variable                | Description                |
| ----------------------- | -------------------------- |
| NOTEBOOKLM_STORAGE_PATH | Path to storage_state.json |
| NOTEBOOKLM_AUTH_JSON    | Inject auth JSON directly  |
| NOTEBOOKLM_HOME         | Base notebooklm directory  |
| NOTEBOOKLM_REST_API_KEY | REST API protection key    |

---

## 🐳 Docker Example

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ⚠️ Disclaimer

This project is **not an official Google NotebookLM API**.

It relies on `notebooklm-py`, which automates NotebookLM web interactions.
Behavior may change if Google updates internal APIs.

Please review applicable terms before production use.

---

## 📜 License

MIT License

---

## 🤝 Contributing

Pull requests and issues are welcome.
