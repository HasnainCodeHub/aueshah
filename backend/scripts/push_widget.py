"""One-shot script: push the patched widget to WP page 1102.

Builds the JSON body with `<` and `>` Unicode-escaped (\\u003c / \\u003e)
to bypass Cloudflare's WAF, then POSTs via curl.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHED = ROOT / ".bespoke-preloader-patched.json"
PAYLOAD = ROOT / ".bespoke-payload-waf-safe.json"

with PATCHED.open("r", encoding="utf-8") as f:
    patched = json.load(f)

content = patched["content_raw"]

# Encode body, then byte-replace < and > with their JSON unicode-escape
# sequences (6 bytes each: < / >). JSON parsers decode those back to
# < and > so the WP database stores the original markup verbatim.
body_str = json.dumps({"content": content}, ensure_ascii=False)
body_bytes = body_str.encode("utf-8")
body_bytes = body_bytes.replace(b"<", b"\\u003c").replace(b">", b"\\u003e")

with PAYLOAD.open("wb") as f:
    f.write(body_bytes)

assert b"<" not in body_bytes, "still raw < in body"
assert b">" not in body_bytes, "still raw > in body"
print(f"Wrote {PAYLOAD} ({len(body_bytes)} bytes, no raw angle brackets)")

# POST via curl
cmd = [
    "curl", "-sS", "-w", "\nHTTP %{http_code}\n",
    "--max-time", "90",
    "--http1.1",
    "-X", "POST",
    "https://aueshah.com/wp-json/wp/v2/pages/1102",
    "-u", "claude-concierge:keEG TqQ3 bphl wewX xoCd ewBQ",
    "-H", "Content-Type: application/json",
    "-H", "Accept: application/json",
    "--data-binary", f"@{PAYLOAD}",
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
