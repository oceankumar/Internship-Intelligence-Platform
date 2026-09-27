import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const failures = [];
page.on("pageerror", (e) => failures.push(e.message));
page.on("console", (m) => {
  if (m.type() === "error") failures.push(m.text());
});
const base = "http://127.0.0.1:3011";
const fixtureJobs = await (
  await page.request.get(base + "/api/internships?limit=100")
).json();
assert.ok(
  fixtureJobs.items.every((j) => j.description.startsWith("TEST FIXTURE.")),
);
for (const job of fixtureJobs.items)
  await page.request.patch(base + "/api/applications/" + job.id, {
    data: { application_status: "not_applied", favorite: false, notes: "" },
  });
await mkdir("test-results", { recursive: true });
await page.goto(base);
await page.locator(".job-card").first().waitFor();
assert.equal(await page.locator(".job-card").count(), 12);
await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
await page.getByRole("button", { name: "Next page" }).click();
await page.waitForFunction(
  () => document.querySelectorAll(".job-card").length === 4,
);
await page.locator(".title-button").first().click();
await page.getByRole("dialog").waitFor();
await page.getByRole("button", { name: "Mark applied", exact: true }).click();
await page.waitForFunction(
  () => document.querySelector("dialog select")?.value === "applied",
);
await page
  .getByLabel("Notes", { exact: true })
  .fill("Browser verification note");
await page.getByRole("button", { name: "Save notes", exact: true }).click();
await page
  .getByRole("button", { name: "Save internship", exact: true })
  .click();
await page.getByRole("button", { name: "Close details", exact: true }).click();
await page.goto(base + "/applications");
await page.locator(".application-row").first().waitFor();
assert.equal(await page.locator(".application-row").count(), 1);
await page.getByRole("button", { name: "Update", exact: true }).click();
await page.getByRole("dialog").waitFor();
assert.equal(
  await page.getByRole("dialog").locator("textarea").inputValue(),
  "Browser verification note",
);
await page.getByRole("button", { name: "Close details", exact: true }).click();
await page.goto(base + "/saved");
await page.locator(".job-card").first().waitFor();
assert.equal(await page.locator(".job-card").count(), 1);
await page.goto(base + "/discover");
await page.locator(".job-card").first().waitFor();
await page.getByLabel("Search opportunities").fill("nonexistent-company");
await page
  .getByRole("heading", { name: "No internships match these filters" })
  .waitFor();
await page.getByRole("button", { name: "Clear search", exact: true }).click();
await page.locator(".job-card").first().waitFor();
await page.getByLabel("Role", { exact: true }).selectOption("frontend");
await page.waitForFunction(
  () => document.querySelectorAll(".job-card").length === 6,
);
await page.getByRole("button", { name: "Save search", exact: true }).click();
await page.getByLabel("Search name").fill("Frontend test");
await page
  .getByRole("dialog")
  .getByRole("button", { name: "Save search", exact: true })
  .click();
await page.getByText("Search saved.", { exact: true }).waitFor();
const exported = await page.request.get(base + "/api/export.csv?role=frontend");
assert.equal(exported.status(), 200);
assert.ok((await exported.text()).includes("Frontend Engineering Intern"));
await page.goto(base + "/profile");
await page
  .getByLabel("Skills, separated by commas")
  .fill("React, JavaScript, TypeScript, HTML");
await page.getByRole("button", { name: "Save profile", exact: true }).click();
await page
  .getByText("Profile saved. Recommendations have been recalculated.")
  .waitFor();
for (const route of ["insights", "sources"]) {
  await page.goto(base + "/" + route);
  await page.waitForLoadState("networkidle");
  assert.equal(await page.locator(".error-banner").count(), 0);
}
await page.setViewportSize({ width: 390, height: 844 });
await page.goto(base + "/discover");
await page.locator(".job-card").first().waitFor();
assert.ok(
  await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  ),
);
await page.screenshot({ path: "test-results/mobile.png", fullPage: false });
await page.getByRole("button", { name: "Filters", exact: true }).click();
await page
  .getByRole("button", { name: "Close filters", exact: true })
  .waitFor({ state: "visible" });
await page.keyboard.press("Escape");
await page.locator(".title-button").first().click();
await page.getByRole("dialog").waitFor();
await page.screenshot({
  path: "test-results/mobile-detail.png",
  fullPage: false,
});
await page.keyboard.press("Escape");
assert.deepEqual(failures, []);
await browser.close();
console.log(
  "PASS: desktop/mobile, pagination, detail, saved roles, status/notes persistence, filtering, saved search, profile, insights, source health, export, no console errors",
);
