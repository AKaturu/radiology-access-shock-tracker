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
const captureCss = `
  header, footer, #MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    display: none !important;
  }
  [data-testid="stAppViewContainer"] > .main {
    background: #f7f9fc;
  }
  [data-testid="stSidebar"] {
    background: #edf1f7;
  }
  .block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
  }
  #radshock-capture-frame {
    position: fixed;
    right: 24px;
    bottom: 24px;
    z-index: 999999;
    width: min(440px, calc(100vw - 48px));
    padding: 18px 20px 16px;
    border: 1px solid rgba(11, 37, 69, 0.14);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 18px 44px rgba(11, 37, 69, 0.16);
    color: #102033;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  #radshock-capture-eyebrow {
    color: #2d6cdf;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  #radshock-capture-title {
    margin-top: 6px;
    font-size: 20px;
    font-weight: 760;
    line-height: 1.18;
  }
  #radshock-capture-caption {
    margin-top: 7px;
    font-size: 14px;
    line-height: 1.38;
    color: #405064;
  }
  #radshock-capture-progress {
    margin-top: 12px;
    height: 4px;
    border-radius: 99px;
    overflow: hidden;
    background: #e2e8f0;
  }
  #radshock-capture-progress > div {
    height: 100%;
    width: var(--progress, 20%);
    background: linear-gradient(90deg, #2d6cdf, #13a38b);
    transition: width 420ms ease;
  }
`;

const screenshots = [
  { name: "dashboard-overview.png", tab: "Overview" },
  { name: "county-shocks.png", tab: "County shocks" },
  { name: "interventions.png", tab: "Interventions" },
  { name: "sensitivity.png", tab: "Sensitivity" },
  { name: "readiness-audit.png", tab: "Readiness" },
];

const walkthrough = [
  {
    tab: "Overview",
    title: "Start with the publication boundary",
    caption:
      "Reviewed North Carolina findings stay separate from 51-jurisdiction readiness evidence.",
  },
  {
    tab: "County shocks",
    title: "Scan county-level access impact",
    caption:
      "The dashboard keeps scores, alerts, and utilization context visible for reviewer triage.",
  },
  {
    tab: "Interventions",
    title: "Compare candidate recovery sites",
    caption:
      "HRSA-based candidates are planning assumptions until source review and local validation.",
  },
  {
    tab: "Sensitivity",
    title: "Stress-test ranking assumptions",
    caption:
      "Alternate weights expose whether priority counties move under reasonable reviewer scenarios.",
  },
  {
    tab: "Readiness",
    title: "Block publication until evidence is ready",
    caption:
      "Readiness checks keep provenance, routing, sensitivity, and claim boundaries auditable.",
  },
];

async function waitForDashboard(page) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByText("Radiology Access Shock Tracker").first().waitFor({ timeout: 30000 });
  await page.addStyleTag({ content: captureCss });
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

async function installNarration(page) {
  await page.evaluate(() => {
    document.querySelector("#radshock-capture-frame")?.remove();
    const frame = document.createElement("div");
    frame.id = "radshock-capture-frame";
    frame.innerHTML = `
      <div id="radshock-capture-eyebrow">Radiology Access Shock Tracker</div>
      <div id="radshock-capture-title"></div>
      <div id="radshock-capture-caption"></div>
      <div id="radshock-capture-progress"><div></div></div>
    `;
    document.body.appendChild(frame);
  });
}

async function setNarration(page, step, index, total) {
  const progress = `${Math.round(((index + 1) / total) * 100)}%`;
  await page.evaluate(
    ({ title, caption, progressValue }) => {
      document.querySelector("#radshock-capture-title").textContent = title;
      document.querySelector("#radshock-capture-caption").textContent = caption;
      document
        .querySelector("#radshock-capture-progress")
        .style.setProperty("--progress", progressValue);
    },
    { title: step.title, caption: step.caption, progressValue: progress },
  );
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

  const screenshotContext = await browser.newContext({
    viewport: { width: 1440, height: 980 },
    deviceScaleFactor: 1,
  });
  const screenshotPage = await screenshotContext.newPage();
  await waitForDashboard(screenshotPage);

  for (const shot of screenshots) {
    await clickTab(screenshotPage, shot.tab);
    await screenshotPage.screenshot({
      path: path.join(outputDir, shot.name),
      fullPage: false,
    });
  }

  await screenshotContext.close();

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

  const videoContext = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: outputDir,
      size: { width: 1280, height: 720 },
    },
  });
  const videoPage = await videoContext.newPage();
  const video = videoPage.video();
  await waitForDashboard(videoPage);
  await installNarration(videoPage);
  for (const [index, step] of walkthrough.entries()) {
    await setNarration(videoPage, step, index, walkthrough.length);
    await clickTab(videoPage, step.tab);
    await videoPage.waitForTimeout(index === 0 ? 1800 : 2400);
  }
  await videoPage.waitForTimeout(1200);
  await videoContext.close();
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
