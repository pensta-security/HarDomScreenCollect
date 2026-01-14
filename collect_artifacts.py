#!/usr/bin/env python3
import argparse
import asyncio
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_") or "output"


def _default_base_name(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    path = parsed.path.replace("/", "_")
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return _slugify(f"{host}{path}_{stamp}")


async def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = args.base_name or _default_base_name(args.url)
    har_path = Path(args.har_path) if args.har_path else output_dir / f"{base_name}.har"
    dom_path = Path(args.dom_path) if args.dom_path else output_dir / f"{base_name}.html"
    screenshot_path = (
        Path(args.screenshot_path) if args.screenshot_path else output_dir / f"{base_name}.png"
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(args.cdp_url)
        context = await browser.new_context(
            ignore_https_errors=True,
            record_har_path=str(har_path),
            record_har_content="embed",
        )
        page = await context.new_page()
        await page.goto(args.url, wait_until="networkidle")

        dom_path.write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(screenshot_path), full_page=True)

        await context.close()
        await browser.close()

    print(f"HAR: {har_path}")
    print(f"DOM: {dom_path}")
    print(f"Screenshot: {screenshot_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect HAR (with embedded content), DOM, and screenshot from a URL."
    )
    parser.add_argument("url", help="URL to load")
    parser.add_argument(
        "--cdp-url",
        default="http://localhost:9222",
        help="Chrome DevTools Protocol endpoint",
    )
    parser.add_argument("--output-dir", default="output", help="Directory for artifacts")
    parser.add_argument("--base-name", help="Base name for output files")
    parser.add_argument("--har-path", help="Explicit HAR file path")
    parser.add_argument("--dom-path", help="Explicit DOM file path")
    parser.add_argument("--screenshot-path", help="Explicit screenshot path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
