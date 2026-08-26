import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/pnoker/Code/micode/web/f1-web/node_modules/playwright-core");
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname));
const slidesDir = path.join(root, "slides");
const imagesDir = root;
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

await fs.mkdir(imagesDir, { recursive: true });
const files = (await fs.readdir(slidesDir)).filter((file) => file.endsWith(".html")).sort();
const browser = await chromium.launch({ executablePath: chromePath, args: ["--force-color-profile=srgb"] });
for (const file of files) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await page.goto(`file://${path.join(slidesDir, file)}`);
  await page.waitForTimeout(250);
  const output = path.join(imagesDir, `${path.basename(file, ".html")}.png`);
  await page.screenshot({ path: output });
  console.log(`✓ ${path.relative(root, output)}`);
  await page.close();
}
await browser.close();
