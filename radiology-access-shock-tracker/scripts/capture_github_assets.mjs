import path from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, readdirSync, rmSync, renameSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  ({ chromium } = require("playwright-core"));
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");
const baseUrl = process.env.RADSHOCK_CAPTURE_URL || "http://127.0.0.1:8765";
const allowSynthetic = process.env.RADSHOCK_CAPTURE_ALLOW_SYNTHETIC === "1";
const chromiumExecutable = process.env.RADSHOCK_CHROMIUM_EXECUTABLE;
const outputDir = path.resolve(
  projectRoot,
  process.env.RADSHOCK_CAPTURE_OUTPUT || "docs/assets/github",
);
const syntheticWarningText = "Synthetic demonstration data are loaded";

const screenshots = [
  { name: "dashboard-overview.png", tab: "Overview" },
  { name: "county-shocks.png", tab: "County shocks" },
  { name: "interventions.png", tab: "Interventions" },
  { name: "sensitivity.png", tab: "Sensitivity" },
  { name: "readiness-audit.png", tab: "Readiness" },
];

async function waitForDashboard(page) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByText("Radiology Access Shock Tracker").first().waitFor({ timeout: 30000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  if (!allowSynthetic && (await page.getByText(syntheticWarningText).count()) > 0) {
    throw new Error(
      "Capture target is synthetic. Set RADSHOCK_ANALYSIS_DIR to a reviewed real analysis " +
        "package, or set RADSHOCK_CAPTURE_ALLOW_SYNTHETIC=1 for intentional demo captures.",
    );
  }
}

async function clickTab(page, tabName) {
  await page.getByRole("tab", { name: tabName }).click();
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1800);
}

async function main() {
  mkdirSync(outputDir, { recursive: true });
  rmSync(path.join(outputDir, "dashboard-walkthrough.webm"), {
    force: true,
  });
  for (const fileName of readdirSync(outputDir)) {
    if (fileName.startsWith("page@") && fileName.endsWith(".webm")) {
      rmSync(path.join(outputDir, fileName), { force: true });
    }
  }
  const browser = await chromium.launch({
    headless: true,
    ...(chromiumExecutable ? { executablePath: chromiumExecutable } : {}),
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 980 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: outputDir,
      size: { width: 1440, height: 980 },
    },
  });
  const page = await context.newPage();
  const video = page.video();
  await waitForDashboard(page);

  for (const shot of screenshots) {
    await clickTab(page, shot.tab);
    await page.screenshot({
      path: path.join(outputDir, shot.name),
      fullPage: false,
    });
  }

  for (const tabName of ["Overview", "County shocks", "Interventions", "Sensitivity", "Readiness"]) {
    await clickTab(page, tabName);
  }

  const mobile = await browser.newPage({
    viewport: { width: 390, height: 900 },
    deviceScaleFactor: 2,
    isMobile: true,
  });
  await waitForDashboard(mobile);
  await mobile.screenshot({
    path: path.join(outputDir, "mobile-overview.png"),
    fullPage: false,
  });
  await mobile.close();

  await context.close();
  if (video) {
    const videoPath = await video.path();
    renameSync(videoPath, path.join(outputDir, "dashboard-walkthrough.webm"));
  }
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
