#!/usr/bin/env python3
import argparse
import asyncio
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

JS_TRACE_CATEGORIES = [
    "devtools.timeline",
    "disabled-by-default-devtools.timeline",
    "v8",
    "v8.execute",
    "disabled-by-default-v8.cpu_profiler",
    "disabled-by-default-v8.cpu_profiler.hires",
    "blink.user_timing",
    "loading",
    "toplevel",
]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_") or "output"


def _default_base_name(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    path = parsed.path.replace("/", "_")
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return _slugify(f"{host}{path}_{stamp}")


async def _start_javascript_trace(context, page):
    cdp_session = await context.new_cdp_session(page)
    tracing_complete = asyncio.get_running_loop().create_future()

    def handle_tracing_complete(params):
        if not tracing_complete.done():
            tracing_complete.set_result(params)

    cdp_session.on("Tracing.tracingComplete", handle_tracing_complete)
    await cdp_session.send(
        "Tracing.start",
        {
            "categories": ",".join(JS_TRACE_CATEGORIES),
            "transferMode": "ReturnAsStream",
        },
    )
    return cdp_session, tracing_complete


async def _stop_javascript_trace(
    cdp_session, tracing_complete, trace_path: Path
) -> None:
    await cdp_session.send("Tracing.end")
    complete_event = await asyncio.wait_for(tracing_complete, timeout=60)
    stream = complete_event.get("stream")
    if not stream:
        trace_path.write_text("", encoding="utf-8")
        return

    try:
        with trace_path.open("w", encoding="utf-8") as trace_file:
            while True:
                chunk = await cdp_session.send("IO.read", {"handle": stream})
                trace_file.write(chunk.get("data", ""))
                if chunk.get("eof"):
                    break
    finally:
        await cdp_session.send("IO.close", {"handle": stream})


async def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = args.base_name or _default_base_name(args.url)
    har_path = Path(args.har_path) if args.har_path else output_dir / f"{base_name}.har"
    dom_path = (
        Path(args.dom_path) if args.dom_path else output_dir / f"{base_name}.html"
    )
    screenshot_path = (
        Path(args.screenshot_path)
        if args.screenshot_path
        else output_dir / f"{base_name}.png"
    )
    js_trace_path = (
        Path(args.js_trace_path)
        if args.js_trace_path
        else output_dir / f"{base_name}.js-trace.json"
    )

    for path in (har_path, dom_path, screenshot_path, js_trace_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(args.cdp_url)
        context_options = {
            "ignore_https_errors": True,
            "record_har_path": str(har_path),
            "record_har_content": "embed",
        }
        if args.proxy_url:
            context_options["proxy"] = {"server": args.proxy_url}

        context = await browser.new_context(
            **context_options,
        )
        page = await context.new_page()
        cdp_session, tracing_complete = await _start_javascript_trace(context, page)

        try:
            await page.goto(args.url, wait_until="networkidle", timeout=300_000)

            dom_path.write_text(await page.content(), encoding="utf-8")
            await page.screenshot(path=str(screenshot_path), full_page=True)
        finally:
            await _stop_javascript_trace(cdp_session, tracing_complete, js_trace_path)
            await context.close()
            await browser.close()

    print(f"HAR: {har_path}")
    print(f"DOM: {dom_path}")
    print(f"Screenshot: {screenshot_path}")
    print(f"JavaScript trace: {js_trace_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect HAR (with embedded content), DOM, screenshot, and Chrome DevTools JavaScript trace from a URL."
    )
    parser.add_argument("url", help="URL to load")
    parser.add_argument(
        "--cdp-url",
        default="http://localhost:9222",
        help="Chrome DevTools Protocol endpoint",
    )
    parser.add_argument(
        "--output-dir", default="output", help="Directory for artifacts"
    )
    parser.add_argument("--base-name", help="Base name for output files")
    parser.add_argument("--har-path", help="Explicit HAR file path")
    parser.add_argument("--dom-path", help="Explicit DOM file path")
    parser.add_argument("--screenshot-path", help="Explicit screenshot path")
    parser.add_argument("--js-trace-path", help="Explicit Chrome trace JSON file path")
    parser.add_argument(
        "--proxy-url",
        help="Proxy URL (e.g., http://127.0.0.1:8080) used to route browser requests",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
