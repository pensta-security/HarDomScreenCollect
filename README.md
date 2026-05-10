# HarDomScreenCollect
Dumps HAR, DOM, screenshot, and Chrome DevTools JavaScript traces for a URL.

## Usage
1. Start Chrome with a remote debugging port:
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/
   ```
2. Install dependencies (Playwright):
   ```bash
   pip install playwright
   playwright install chromium
   ```
3. Run the collector:
   ```bash
   python collect_artifacts.py https://example.com
   ```

   To route all requests through Burp (or another proxy), pass `--proxy-url`:
   ```bash
   python collect_artifacts.py https://example.com --proxy-url http://127.0.0.1:8080
   ```

Artifacts are written to the `output/` directory by default.

## Artifacts
For each run, the collector writes:

- A HAR file with embedded response content (`.har`).
- A DOM snapshot (`.html`).
- A full-page screenshot (`.png`).
- A Chrome trace file with JavaScript execution activity (`.js-trace.json`).

The JavaScript trace is collected through Chrome DevTools Protocol tracing rather than by
wrapping page functions. This avoids monkey-patching the page and captures native trace
events such as script evaluation, function-call timeline events, event dispatch, user
timing, loading activity, and V8 CPU-profiler call stacks. The output is Chrome trace JSON
and can be inspected with Chrome DevTools Performance tools or Perfetto.

To choose the trace path explicitly, pass `--js-trace-path`:
```bash
python collect_artifacts.py https://example.com --js-trace-path output/example.js-trace.json
```
