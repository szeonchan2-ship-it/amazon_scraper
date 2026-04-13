import html
import os
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from parse_pasted_reviews import parse_reviews, write_reviews_csv


OUTPUT_FILE = "parsed_reviews.csv"
STATE = {"raw_text": "", "records": []}


def build_page(raw_text: str, records) -> str:
    rows = []
    for row in records:
        rows.append(
            "<tr>"
            f"<td>{html.escape(row.get('rating', ''))}</td>"
            f"<td>{html.escape(row.get('title', ''))}</td>"
            f"<td>{html.escape(row.get('content', ''))}</td>"
            "</tr>"
        )
    table_rows = "\n".join(rows) or "<tr><td colspan='3' style='color:#666'>No parsed rows yet.</td></tr>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Amazon Review Parser</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 0; background: #f5f6f8; color: #111; }}
    .top {{ padding: 14px 16px; border-bottom: 1px solid #ddd; background: white; display: flex; gap: 10px; align-items: center; }}
    .top .meta {{ margin-left: auto; color: #555; font-size: 14px; }}
    .wrap {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px; height: calc(100vh - 70px); box-sizing: border-box; }}
    .card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; min-height: 0; }}
    h3 {{ margin: 4px 0 10px; font-size: 15px; }}
    textarea {{ width: 100%; height: 100%; resize: none; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; padding: 10px; box-sizing: border-box; }}
    .actions {{ display: flex; gap: 8px; margin-bottom: 10px; }}
    button, a.btn {{ border: 1px solid #bbb; background: #fff; border-radius: 6px; padding: 8px 12px; cursor: pointer; text-decoration: none; color: #111; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }}
    th, td {{ border: 1px solid #ddd; padding: 6px; vertical-align: top; word-break: break-word; }}
    th {{ background: #f2f2f2; text-align: left; }}
    .table-wrap {{ overflow: auto; height: 100%; }}
  </style>
</head>
<body>
  <div class="top">
    <strong>Amazon Review Parser UI</strong>
    <span class="meta">Parsed rows: {len(records)}</span>
  </div>
  <div class="wrap">
    <div class="card">
      <h3>Left: Paste Raw Reviews</h3>
      <form method="post" action="/">
        <div class="actions">
          <button type="submit">Parse</button>
          <a class="btn" href="/download">Download CSV</a>
        </div>
        <textarea name="raw_text" placeholder="Paste review text here...">{html.escape(raw_text)}</textarea>
      </form>
    </div>
    <div class="card">
      <h3>Right: Parsed Output (rating / title / content)</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th style="width:80px">Rating</th><th style="width:220px">Title</th><th>Content</th></tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send_html(self, body: str, code: int = 200):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/download":
            if not os.path.exists(OUTPUT_FILE):
                self._send_html(build_page(STATE["raw_text"], STATE["records"]))
                return
            with open(OUTPUT_FILE, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{OUTPUT_FILE}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_html(build_page(STATE["raw_text"], STATE["records"]))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        raw_text = form.get("raw_text", [""])[0]
        records = parse_reviews(raw_text)
        STATE["raw_text"] = raw_text
        STATE["records"] = records
        write_reviews_csv(records, OUTPUT_FILE)
        self._send_html(build_page(raw_text, records))

    def log_message(self, format, *args):
        return


def _pick_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Opening web UI at {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
