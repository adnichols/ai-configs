// Lets agent browsers open Access-protected prototypes on *.demos.keramos.tech.
// The demos service token stays in this process: it is sent only to demo hosts,
// and the browser receives only the short-lived CF_Authorization cookie that
// Cloudflare Access issues in exchange.
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const DEMO_ACCESS_ENV = join(homedir(), ".config", "ccore", "demos-access.env");
const DEMO_DOMAIN = "demos.keramos.tech";

export function isDemoUrl(url) {
  const { protocol, hostname } = new URL(url);
  return protocol === "https:" && hostname.endsWith(`.${DEMO_DOMAIN}`);
}

function readToken() {
  let text;
  try {
    text = readFileSync(DEMO_ACCESS_ENV, "utf8");
  } catch {
    throw new Error(
      `Missing ${DEMO_ACCESS_ENV}. It holds the "CCore agents demos" Access service token ` +
        "(DEMOS_ACCESS_CLIENT_ID, DEMOS_ACCESS_CLIENT_SECRET); ask the operator to install it on this host.",
    );
  }
  const values = Object.fromEntries(
    text.split("\n").filter((line) => line.includes("=")).map((line) => {
      const at = line.indexOf("=");
      return [line.slice(0, at).trim(), line.slice(at + 1).trim()];
    }),
  );
  const id = values.DEMOS_ACCESS_CLIENT_ID;
  const secret = values.DEMOS_ACCESS_CLIENT_SECRET;
  if (!id || !secret) throw new Error(`${DEMO_ACCESS_ENV} must set DEMOS_ACCESS_CLIENT_ID and DEMOS_ACCESS_CLIENT_SECRET.`);
  return { id, secret };
}

// Returns cookies accepted by Playwright `context.addCookies` and by
// Puppeteer/OMP `setCookies`. Add them before the first navigation.
export async function demoAccessCookies(url) {
  if (!isDemoUrl(url)) throw new Error(`Refusing to send the demos service token to ${url}; only https://*.${DEMO_DOMAIN} is allowed.`);
  const { id, secret } = readToken();
  const response = await fetch(url, {
    redirect: "manual",
    headers: { "CF-Access-Client-Id": id, "CF-Access-Client-Secret": secret },
  });
  const header = response.headers.getSetCookie().find((cookie) => cookie.startsWith("CF_Authorization="));
  if (!header) {
    throw new Error(`Cloudflare Access did not accept the demos service token for ${url} (HTTP ${response.status}).`);
  }
  const [pair, ...attributes] = header.split(";").map((part) => part.trim());
  const expires = attributes.find((part) => part.toLowerCase().startsWith("expires="));
  return [{
    name: "CF_Authorization",
    value: pair.slice("CF_Authorization=".length),
    domain: new URL(url).hostname,
    path: "/",
    expires: expires ? Math.floor(Date.parse(expires.slice("expires=".length)) / 1000) : -1,
    secure: true,
    httpOnly: false,
    sameSite: "None",
  }];
}

// CLI: `demo-access.mjs check <url>` prints the HTTP status a browser holding
// the Access cookie receives. It never prints the token or the cookie.
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [command, url] = process.argv.slice(2);
  if (command !== "check" || !url) {
    console.error("usage: demo-access.mjs check https://<run>.demos.keramos.tech/");
    process.exit(2);
  }
  try {
    const [cookie] = await demoAccessCookies(url);
    const response = await fetch(url, { redirect: "manual", headers: { Cookie: `${cookie.name}=${cookie.value}` } });
    console.log(`${response.status} ${url}`);
    process.exit(response.ok ? 0 : 1);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
