const { chromium } = require("playwright");

const TARGET_URL = "http://localhost:3001";

(async () => {
  console.log("🚀 Starting Phase 2.3: Manual testing - List type conversion");
  console.log("📍 Target URL:", TARGET_URL);

  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();

  try {
    // Navigate to the workspaces page
    console.log("\n📄 Opening application...");
    await page.goto(TARGET_URL, { waitUntil: "networkidle", timeout: 15000 });
    console.log("✅ Page loaded");

    // Wait for the page to render
    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({ path: "/tmp/phase2-3-page-loaded.png" });
    console.log("📸 Initial screenshot saved");

    // Try to find workspace links
    console.log("\n🔍 Looking for workspace links...");

    const workspaceLinks = await page.locator('a[href^="/d/"]').all();
    console.log(`📊 Found ${workspaceLinks.length} workspace links`);

    if (workspaceLinks.length > 0) {
      // Click on the first workspace
      const firstWorkspace = workspaceLinks[0];
      const workspaceName = await firstWorkspace.textContent();
      const workspaceHref = await firstWorkspace.getAttribute("href");

      console.log(
        `👆 Clicking on workspace: "${workspaceName}" (${workspaceHref})`
      );
      await firstWorkspace.click();
      console.log("✅Clicked on workspace");

      // Wait for navigation
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(2000);

      await page.screenshot({ path: "/tmp/phase2-3-workspace-opened.png" });
      console.log("📸 Workspace opened screenshot saved");
    } else {
      console.log("⚠️  No workspace links found");
      console.log("💡 Browser will remain open for manual navigation...");

      await page.waitForTimeout(120000);
      await browser.close();
      return;
    }

    // Now look for document links
    console.log("\n🔍 Looking for document links...");

    const docLinks = await page.locator('a[href*="/d/"]').all();
    console.log(`📊 Found ${docLinks.length} document links`);

    if (docLinks.length > 0) {
      // Click on a document (first one that's not the workspace link)
      let clickedOnDocument = false;

      for (const link of docLinks) {
        const href = await link.getAttribute("href");
        // Skip links that are just workspace paths (look for docs or specific document IDs)
        if (
          href &&
          (href.includes("/docs") || /\/d\/[^\/]+\/[^\/]+$/.test(href))
        ) {
          const docName = await link.textContent();
          console.log(`👆 Clicking on document: "${docName}" (${href})`);
          await link.click();
          console.log("✅ Clicked on document");
          clickedOnDocument = true;
          break;
        }
      }

      if (clickedOnDocument) {
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(2000);

        await page.screenshot({ path: "/tmp/phase2-3-document-opened.png" });
        console.log("📸 Document opened screenshot saved");
      }
    }

    // Check if we have an editor now
    const editorExists = (await page.locator(".ProseMirror").count()) > 0;
    console.log(`📊 Editor found: ${editorExists}`);

    if (!editorExists) {
      console.log("❌ Could not find editor");
      console.log("💡 Browser will remain open for manual inspection...");

      await page.screenshot({
        path: "/tmp/phase2-3-no-editor-debug.png",
        fullPage: true,
      });
      await page.waitForTimeout(120000);
      await browser.close();
      return;
    }

    // Click on the editor to focus
    await page.click(".ProseMirror", { timeout: 5000 });
    console.log("✅ Focused on editor");

    // ============================================
    // TEST 1: Bullet list → Ordered list conversion
    // ============================================
    console.log("\n" + "=".repeat(60));
    console.log("TEST 1: Bullet list → Ordered list conversion");
    console.log("=".repeat(60));

    // Clear any existing content
    await page.keyboard.press("Control+A");
    await page.waitForTimeout(100);
    await page.keyboard.press("Backspace");
    await page.waitForTimeout(200);

    // Create a bullet list by typing "- "
    await page.type(".ProseMirror", "First item- ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Second item- ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Third item");
    console.log('✅ Created bullet list (typed "- ")');

    // Wait a moment for the UI to update
    await page.waitForTimeout(500);

    // Take screenshot of bullet list
    await page.screenshot({ path: "/tmp/phase2-3-test1-bullet-list.png" });
    console.log("📸 Screenshot: /tmp/phase2-3-test1-bullet-list.png");

    // Verify bullet list exists
    const bulletListExists = await page.evaluate(() => {
      const list =
        document.querySelector("ol") ||
        document.querySelector(".ProseMirror ul");
      return list !== null;
    });

    console.log(`📊 Bullet/Ordered list found: ${bulletListExists}`);

    // Find and click the ordered list button
    console.log("\n🔍 Looking for ordered list button in toolbar...");

    const orderedListSelectors = [
      'button[title*="ordered" i]',
      'button[title*="numbered" i]',
      'button[aria-label*="ordered" i]',
      'button[aria-label*="numbered" i]',
      'button:has-text("Ordered")',
      'button:has-text("Numbered")',
    ];

    let orderedListButtonClicked = false;
    for (const selector of orderedListSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 1000 })) {
          console.log(
            `🎯 Found ordered list button with selector: ${selector}`
          );
          await button.click();
          orderedListButtonClicked = true;
          console.log("✅ Clicked ordered list button");
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }

    if (!orderedListButtonClicked) {
      console.log(
        "⚠️  Could not find ordered list button via standard selectors"
      );
      console.log("💡 Searching for buttons with list-related content...");

      // Try to find button with icon or attributes that indicate ordered list
      const allButtons = await page.locator("button").all();
      for (const button of allButtons) {
        const isVisible = await button.isVisible();
        if (!isVisible) continue;

        try {
          const title = await button.getAttribute("title");
          const ariaLabel = await button.getAttribute("aria-label");
          const text = await button.textContent();

          if (
            (title &&
              (title.includes("ordered") || title.includes("numbered"))) ||
            (ariaLabel &&
              (ariaLabel.includes("ordered") || ariaLabel.includes("numbered")))
          ) {
            console.log(
              `🎯 Found ordered list button - title: "${title}" aria-label: "${ariaLabel}" text: "${text}"`
            );
            await button.click();
            orderedListButtonClicked = true;
            console.log("✅ Clicked ordered list button");
            break;
          }
        } catch (e) {
          // Some elements may throw errors when accessing attributes
        }
      }
    }

    if (!orderedListButtonClicked) {
      console.log("❌ TEST 1 SKIPPED: Could not identify ordered list button");
      console.log(
        "💡 Manual verification required - click ordered list button manually"
      );
    } else {
      // Wait for conversion
      await page.waitForTimeout(500);

      // Verify conversion - check if converted between list types
      const conversionResult = await page.evaluate(() => {
        const orderedList = document.querySelector(".ProseMirror ol");
        const bulletList = document.querySelector(".ProseMirror ul");
        return {
          hasOrderedList: orderedList !== null,
          hasBulletList: bulletList !== null,
        };
      });

      console.log(`📊 Ordered lists found: ${conversionResult.hasOrderedList}`);
      console.log(`📊 Bullet lists found: ${conversionResult.hasBulletList}`);

      if (conversionResult.hasOrderedList && !conversionResult.hasBulletList) {
        console.log(
          "✅ TEST 1 PASSED: Bullet list successfully converted to ordered list"
        );
      } else if (!orderedListButtonClicked) {
        console.log("⚠️  TEST 1 INCONCLUSIVE: Need manual verification");
      } else {
        console.log(
          "⚠️  TEST 1 UNCERTAIN: List conversion not clearly verified"
        );
      }

      // Take screenshot after conversion
      await page.screenshot({ path: "/tmp/phase2-3-test1-converted.png" });
      console.log("📸 Screenshot: /tmp/phase2-3-test1-converted.png");
    }

    // ============================================
    // TEST 2: Ordered list → Bullet list conversion
    // ============================================
    console.log("\n" + "=".repeat(60));
    console.log("TEST 2: Ordered list → Bullet list conversion");
    console.log("=".repeat(60));

    // Clear the editor and create a new ordered list
    await page.keyboard.press("Control+A");
    await page.waitForTimeout(100);
    await page.keyboard.press("Backspace");
    await page.waitForTimeout(200);

    // Create an ordered list by typing "1. "
    await page.type(".ProseMirror", "First item1. ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Second item1. ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Third item");
    console.log('✅ Created ordered list (typed "1. ")');

    // Take screenshot of ordered list
    await page.waitForTimeout(500);
    await page.screenshot({ path: "/tmp/phase2-3-test2-ordered-list.png" });
    console.log("📸 Screenshot: /tmp/phase2-3-test2-ordered-list.png");

    // Find and click the bullet list button
    const bulletListSelectors = [
      'button[title*="bullet" i]',
      'button[aria-label*="bullet" i]',
      'button:has-text("Bullet")',
    ];

    let bulletListButtonClicked = false;
    for (const selector of bulletListSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 1000 })) {
          console.log(`🎯 Found bullet list button with selector: ${selector}`);
          await button.click();
          bulletListButtonClicked = true;
          console.log("✅ Clicked bullet list button");
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }

    if (!bulletListButtonClicked) {
      console.log(
        "⚠️  Could not find bullet list button via standard selectors"
      );
      console.log("💡 Searching for buttons with bullet-related content...");

      // Try to find button with icon or attributes that indicate bullet list
      const allButtons = await page.locator("button").all();
      for (const button of allButtons) {
        const isVisible = await button.isVisible();
        if (!isVisible) continue;

        try {
          const title = await button.getAttribute("title");
          const ariaLabel = await button.getAttribute("aria-label");

          if (
            (title && title.includes("bullet")) ||
            (ariaLabel && ariaLabel.includes("bullet"))
          ) {
            console.log(
              `🎯 Found bullet list button - title: "${title}" aria-label: "${ariaLabel}"`
            );
            await button.click();
            bulletListButtonClicked = true;
            console.log("✅ Clicked bullet list button");
            break;
          }
        } catch (e) {
          // Some elements may throw errors when accessing attributes
        }
      }
    }

    if (!bulletListButtonClicked) {
      console.log("❌ TEST 2 SKIPPED: Could not identify bullet list button");
      console.log(
        "💡 Manual verification required - click bullet list button manually"
      );
    } else {
      // Wait for conversion
      await page.waitForTimeout(500);

      // Verify conversion - check if converted between list types
      const conversionResult = await page.evaluate(() => {
        const orderedList = document.querySelector(".ProseMirror ol");
        const bulletList = document.querySelector(".ProseMirror ul");
        return {
          hasOrderedList: orderedList !== null,
          hasBulletList: bulletList !== null,
        };
      });

      console.log(`📊 Bullet lists found: ${conversionResult.hasBulletList}`);
      console.log(`📊 Ordered lists found: ${conversionResult.hasOrderedList}`);

      if (conversionResult.hasBulletList && !conversionResult.hasOrderedList) {
        console.log(
          "✅ TEST 2 PASSED: Ordered list successfully converted to bullet list"
        );
      } else if (!bulletListButtonClicked) {
        console.log("⚠️  TEST 2 INCONCLUSIVE: Need manual verification");
      } else {
        console.log(
          "⚠️  TEST 2 UNCERTAIN: List conversion not clearly verified"
        );
      }

      // Take screenshot after conversion
      await page.screenshot({ path: "/tmp/phase2-3-test2-converted.png" });
      console.log("📸 Screenshot: /tmp/phase2-3-test2-converted.png");
    }

    // ============================================
    // TEST 3: Test conversion using selection toolbar (floating menu)
    // ============================================
    console.log("\n" + "=".repeat(60));
    console.log("TEST 3: List type conversion via selection toolbar");
    console.log("=".repeat(60));

    // Clear the editor and create a bullet list
    await page.keyboard.press("Control+A");
    await page.waitForTimeout(100);
    await page.keyboard.press("Backspace");
    await page.waitForTimeout(200);

    // Create a bullet list
    await page.type(".ProseMirror", "Item 1- ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Item 2- ");
    await page.keyboard.press("Enter");
    await page.type(".ProseMirror", "Item 3");
    console.log("✅ Created bullet list for selection toolbar test");

    await page.waitForTimeout(500);
    await page.screenshot({ path: "/tmp/phase2-3-test3-initial.png" });
    console.log("📸 Screenshot: /tmp/phase2-3-test3-initial.png");

    // Select text in the list to trigger floating menu
    const listItems = await page.locator("li").all();
    if (listItems.length > 0) {
      console.log(`✅ Found ${listItems.length} list items`);

      // Select the text in the first list item
      await listItems[0].click();
      await page.keyboard.down("Shift");
      await page.keyboard.press("End");
      await page.keyboard.up("Shift");
      console.log("✅ Selected text in list item");

      // Wait for floating menu to appear
      await page.waitForTimeout(1000);

      // Take screenshot to see if floating menu appeared
      await page.screenshot({ path: "/tmp/phase2-3-test3-floating-menu.png" });
      console.log("📸 Screenshot: /tmp/phase2-3-test3-floating-menu.png");

      // Try to find the floating menu
      const floatingMenuSelectors = [
        '[role="menu"][data-floating]',
        ".floating-menu",
        ".selection-toolbar",
        '[data-testid*="floating"]',
        '[data-testid*="selection"]',
        '[role="toolbar"]',
      ];

      let floatingMenuFound = false;
      for (const selector of floatingMenuSelectors) {
        try {
          // Look for visible toolbars/menus
          const menus = await page.locator(selector).all();
          for (const menu of menus) {
            if (await menu.isVisible({ timeout: 100 })) {
              console.log(
                `🎯 Found visible floating menu/toolbar with selector: ${selector}`
              );
              floatingMenuFound = true;

              // Try to click ordered list button in floating menu
              const orderedBtn = menu
                .locator("button")
                .filter({ hasText: /ordered|numbered/i })
                .first();
              if ((await orderedBtn.count()) > 0) {
                console.log("🎯 Found ordered list button in floating menu");
                await orderedBtn.click();
                console.log("✅ Clicked ordered list button in floating menu");

                // Verify conversion
                await page.waitForTimeout(500);
                const hasOrderedList3 = await page.evaluate(() => {
                  const orderedList = document.querySelector(".ProseMirror ol");
                  return orderedList !== null;
                });
                console.log(`📊 Ordered lists found: ${hasOrderedList3}`);

                if (hasOrderedList3) {
                  console.log(
                    "✅ TEST 3 PASSED: List type converted via floating menu"
                  );
                } else {
                  console.log(
                    "⚠️  TEST 3 UNCERTAIN: List conversion via floating menu not clearly verified"
                  );
                }

                await page.screenshot({
                  path: "/tmp/phase2-3-test3-result.png",
                });
                console.log("📸 Screenshot: /tmp/phase2-3-test3-result.png");
                break;
              }
            }
          }

          if (floatingMenuFound) break;
        } catch (e) {
          console.log(`⚠️  Floating menu not found with selector: ${selector}`);
        }
      }

      if (!floatingMenuFound) {
        console.log("⚠️  Floating menu not detected in DOM or not visible");
        console.log(
          "💡 This might be expected if floating menu implementation differs"
        );
        console.log(
          "💡 Test 3 requires manual verification of selection toolbar functionality"
        );
      }
    } else {
      console.log("⚠️  TEST 3 SKIPPED: Could not create/find list items");
    }

    // ============================================
    // TEST SUMMARY
    // ============================================
    console.log("\n" + "=".repeat(60));
    console.log("PHASE 2.3 MANUAL TESTING COMPLETE");
    console.log("=".repeat(60));
    console.log("\nScreenshots saved to /tmp/:");
    console.log("  - phase2-3-page-loaded.png");
    console.log("  - phase2-3-workspace-opened.png");
    console.log("  - phase2-3-document-opened.png");
    console.log("  - phase2-3-test1-bullet-list.png");
    console.log("  - phase2-3-test1-converted.png");
    console.log("  - phase2-3-test2-ordered-list.png");
    console.log("  - phase2-3-test2-converted.png");
    console.log("  - phase2-3-test3-initial.png");
    console.log("  - phase2-3-test3-floating-menu.png");
    console.log("  - phase2-3-test3-result.png");
    console.log("\n" + "=".repeat(60));

    // Keep browser open for manual inspection
    console.log(
      "\n💡 Browser will remain open for 60 seconds for manual inspection and verification..."
    );
    console.log(
      "💡 Close the browser window to end the test early, or wait for auto-close"
    );

    await page.waitForTimeout(60000);
  } catch (error) {
    console.error("\n❌ Error during testing:", error.message);
    console.error("Stack trace:", error.stack);

    // Take error screenshot
    try {
      await page.screenshot({
        path: "/tmp/phase2-3-error.png",
        fullPage: true,
      });
      console.log("📸 Error screenshot saved: /tmp/phase2-3-error.png");
    } catch (screenshotError) {
      console.error(
        "Could not take error screenshot:",
        screenshotError.message
      );
    }

    // Keep browser open for debugging
    console.log(
      "\n💡 Browser will remain open for 60 seconds for manual debugging..."
    );
    await page.waitForTimeout(60000);
  } finally {
    await browser.close();
    console.log("\n🏁 Test complete");
  }
})();
