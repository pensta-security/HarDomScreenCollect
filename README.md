# HarDomScreenCollect
Dumps HAR, Dom and Screenshot for URL

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

Artifacts are written to the `output/` directory by default.
