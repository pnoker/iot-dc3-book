import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/pnoker/Code/micode/web/f1-web/node_modules/playwright-core");
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname));
const slidesDir = path.join(root, "slides");
const imagesDir = path.join(root, "images");
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

await fs.mkdir(imagesDir, { recursive: true });
const files = (await fs.readdir(slidesDir)).filter((file) => file.endsWith(".html")).sort();
const browser = await chromium.launch({ executablePath: chromePath, args: ["--force-color-profile=srgb"] });
for (const file of files) {
  const url = `file://${path.join(slidesDir, file)}`;
  // 预打开读取 <body data-w/data-h> 自定义画幅(默认 1280×720),公众号封面 2.35:1 / 1:1 用
  const probe = await browser.newPage();
  await probe.goto(url);
  const [w, h] = await probe.evaluate(() => [
    Number(document.body.dataset.w) || 1280,
    Number(document.body.dataset.h) || 720,
  ]);
  await probe.close();
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  await page.goto(url);
  await page.waitForTimeout(250);
  const output = path.join(imagesDir, `${path.basename(file, ".html")}.png`);
  await page.screenshot({ path: output });
  console.log(`✓ ${path.relative(root, output)} (${w}×${h}@2x)`);
  await page.close();
}
await browser.close();
