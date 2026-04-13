import csv
import io
import os
import uuid
from threading import Thread
from typing import List, Tuple

import requests
from flask import Flask, Response, jsonify, redirect, render_template_string, request, url_for


app = Flask(__name__)
GENERATED_FILES = {}
JOBS = {}

DEFAULT_MODEL = "gpt-5.4-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


PAGE_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CSV Summary Generator</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; margin: 0; background: #f5f6f8; color: #111; }
    .container { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; }
    .field { display: flex; flex-direction: column; gap: 6px; min-width: 220px; flex: 1; }
    label { font-size: 13px; color: #444; }
    input, textarea, select, button { font-size: 14px; border: 1px solid #bbb; border-radius: 6px; padding: 8px; }
    textarea { min-height: 90px; }
    button { background: #fff; cursor: pointer; }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
    th, td { border: 1px solid #ddd; padding: 6px; vertical-align: top; word-break: break-word; }
    th { background: #f1f1f1; text-align: left; }
    .muted { color: #666; }
    .error { color: #b00020; font-weight: 600; }
    .ok { color: #1b7f2a; font-weight: 600; }
    .hidden { display: none; }
    .progress { font-size: 14px; color: #333; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h2>CSV Summary Generator</h2>
      <p class="muted">Upload CSV, the app reads column 3 (index 2), calls ChatGPT API row-by-row, and appends a <code>summary</code> column.</p>
      <form id="gen-form" enctype="multipart/form-data">
        <div class="row">
          <div class="field">
            <label>CSV file</label>
            <input id="csv-file" type="file" name="csv_file" accept=".csv,text/csv" required />
          </div>
          <div class="field">
            <label>Model</label>
            <input id="model" type="text" name="model" value="{{ model }}" />
          </div>
          <div class="field">
            <label>OpenAI API Key (optional if OPENAI_API_KEY is set)</label>
            <input id="api-key" type="password" name="api_key" placeholder="sk-..." />
          </div>
        </div>
        <div class="field" style="margin-top:10px;">
          <label>Your summary instruction (Chinese/English both ok)</label>
          <textarea id="instruction" name="instruction" required>{{ instruction }}</textarea>
        </div>
        <div style="margin-top:10px;">
          <button id="generate-btn" type="submit">Generate Summary Column</button>
          <span id="progress-text" class="progress hidden"></span>
        </div>
      </form>
      <p id="error-text" class="error hidden"></p>
      <p id="ok-text" class="ok hidden"></p>
      <p id="download-wrap" class="hidden"><a id="download-link" href="#">Download generated CSV</a></p>
    </div>

    <div class="split">
      <div class="card">
        <h3>Column 3 Input Preview</h3>
        <table>
          <thead><tr><th>#</th><th>content (col 3)</th></tr></thead>
          <tbody id="left-preview">
            <tr><td colspan="2" style="color:#666">No parsed rows yet.</td></tr>
          </tbody>
        </table>
      </div>
      <div class="card">
        <h3>Generated Summary Preview</h3>
        <table>
          <thead><tr><th>#</th><th>summary</th></tr></thead>
          <tbody id="right-preview">
            <tr><td colspan="2" style="color:#666">No generated summaries yet.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const form = document.getElementById("gen-form");
    const generateBtn = document.getElementById("generate-btn");
    const progressText = document.getElementById("progress-text");
    const errorText = document.getElementById("error-text");
    const okText = document.getElementById("ok-text");
    const downloadWrap = document.getElementById("download-wrap");
    const downloadLink = document.getElementById("download-link");
    const leftPreview = document.getElementById("left-preview");
    const rightPreview = document.getElementById("right-preview");

    function escapeHtml(str) {
      return (str || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function setMessage({ error = "", ok = "" }) {
      if (error) {
        errorText.textContent = error;
        errorText.classList.remove("hidden");
      } else {
        errorText.classList.add("hidden");
      }
      if (ok) {
        okText.textContent = ok;
        okText.classList.remove("hidden");
      } else {
        okText.classList.add("hidden");
      }
    }

    function renderPreview(rows) {
      if (!rows || rows.length === 0) {
        leftPreview.innerHTML = "<tr><td colspan='2' style='color:#666'>No parsed rows yet.</td></tr>";
        rightPreview.innerHTML = "<tr><td colspan='2' style='color:#666'>No generated summaries yet.</td></tr>";
        return;
      }

      leftPreview.innerHTML = rows
        .map((r) => `<tr><td>${r.idx}</td><td>${escapeHtml(r.content)}</td></tr>`)
        .join("");
      rightPreview.innerHTML = rows
        .map((r) => `<tr><td>${r.idx}</td><td>${escapeHtml(r.summary || "")}</td></tr>`)
        .join("");
    }

    async function pollJob(jobId) {
      while (true) {
        const res = await fetch(`/status/${jobId}`);
        const data = await res.json();

        if (data.error) {
          setMessage({ error: data.error });
          generateBtn.disabled = false;
          progressText.classList.add("hidden");
          return;
        }

        renderPreview(data.preview_rows || []);
        progressText.textContent = `Processing: ${data.completed}/${data.total}`;
        progressText.classList.remove("hidden");

        if (data.status === "done") {
          setMessage({ ok: `Done. Generated summary for ${data.total} rows.` });
          if (data.download_url) {
            downloadLink.href = data.download_url;
            downloadWrap.classList.remove("hidden");
          }
          generateBtn.disabled = false;
          progressText.classList.add("hidden");
          return;
        }

        if (data.status === "error") {
          setMessage({ error: data.error || "Job failed." });
          generateBtn.disabled = false;
          progressText.classList.add("hidden");
          return;
        }

        await new Promise((resolve) => setTimeout(resolve, 900));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setMessage({});
      downloadWrap.classList.add("hidden");
      generateBtn.disabled = true;
      progressText.textContent = "Uploading and preparing...";
      progressText.classList.remove("hidden");

      const fd = new FormData(form);
      const res = await fetch("/start", { method: "POST", body: fd });
      const data = await res.json();

      if (data.error) {
        setMessage({ error: data.error });
        generateBtn.disabled = false;
        progressText.classList.add("hidden");
        return;
      }

      await pollJob(data.job_id);
    });
  </script>
</body>
</html>
"""


def call_openai_summary(api_key: str, model: str, instruction: str, content: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise assistant that writes one summary for each input row.",
            },
            {
                "role": "user",
                "content": (
                    f"Instruction:\n{instruction}\n\n"
                    f"Text from CSV column 3:\n{content}\n\n"
                    "Return summary text only."
                ),
            },
        ],
        "temperature": 0.2,
    }
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def parse_csv(file_storage) -> Tuple[List[str], List[List[str]]]:
    raw = file_storage.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty.")
    header = rows[0]
    data_rows = rows[1:]
    return header, data_rows


@app.get("/")
def index():
    return render_template_string(
        PAGE_TEMPLATE,
        model=DEFAULT_MODEL,
        instruction="Summarize each review in one short sentence.",
    )


def process_job(job_id: str, header: List[str], data_rows: List[List[str]], instruction: str, model: str, api_key: str) -> None:
    try:
        output_header = list(header) + ["summary"]
        output_rows = []
        preview_rows = []

        for idx, row in enumerate(data_rows, start=1):
            content = row[2] if len(row) > 2 else ""
            summary = call_openai_summary(api_key, model, instruction, content) if content.strip() else ""
            output_rows.append(list(row) + [summary])
            preview_rows.append({"idx": idx, "content": content, "summary": summary})

            JOBS[job_id]["completed"] = idx
            JOBS[job_id]["preview_rows"] = preview_rows

        out_buffer = io.StringIO()
        writer = csv.writer(out_buffer, quoting=csv.QUOTE_ALL)
        writer.writerow(output_header)
        writer.writerows(output_rows)
        csv_bytes = out_buffer.getvalue().encode("utf-8")

        token = str(uuid.uuid4())
        GENERATED_FILES[token] = csv_bytes
        download_url = url_for("download", token=token)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["download_url"] = download_url
    except requests.HTTPError as exc:
        err = exc.response.text[:400] if exc.response is not None else str(exc)
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = f"OpenAI API error: {err}"
    except Exception as exc:  # noqa: BLE001
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = f"Failed: {exc}"


@app.post("/start")
def start():
    csv_file = request.files.get("csv_file")
    instruction = (request.form.get("instruction") or "").strip()
    model = (request.form.get("model") or DEFAULT_MODEL).strip()
    api_key = (request.form.get("api_key") or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()

    if not csv_file:
        return jsonify({"error": "Please upload a CSV file."}), 400
    if not instruction:
        return jsonify({"error": "Please provide your summary instruction."}), 400
    if not api_key:
        return jsonify({"error": "Missing API key. Fill the field or set OPENAI_API_KEY."}), 400

    header, data_rows = parse_csv(csv_file)
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "running",
        "completed": 0,
        "total": len(data_rows),
        "preview_rows": [],
        "download_url": "",
        "error": "",
    }

    thread = Thread(
        target=process_job,
        args=(job_id, header, data_rows, instruction, model, api_key),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.get("/status/<job_id>")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(job)


@app.get("/download/<token>")
def download(token: str):
    data = GENERATED_FILES.get(token)
    if data is None:
        return redirect(url_for("index"))
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="summary_output.csv"'},
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
