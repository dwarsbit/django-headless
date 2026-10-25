// End-to-end tests of the client against a real Django project (e2e/django):
//
// 1. create a database with test data and start the development server;
// 2. generate the types with the CLI, from the schema route;
// 3. type-check and run the end-to-end tests (e2e/*.e2e.test.ts);
// 4. with --next, install the packed package in a Next.js app (e2e/next-app),
//    load it with require(), build the app against the API and request its
//    pages, including a route on the edge runtime.
//
// Run it with the Python environment of the repository, from client/:
//
//     poetry run npm run e2e        (or e2e:next, with the Next.js app)
//
// PYTHON sets the Python command (default: python).
import { spawn } from "node:child_process";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const e2eDir = dirname(fileURLToPath(import.meta.url));
const clientDir = dirname(e2eDir);
const djangoDir = join(e2eDir, "django");
const nextDir = join(e2eDir, "next-app");
const python = process.env.PYTHON ?? "python";
const djangoPort = Number(process.env.E2E_DJANGO_PORT ?? 8765);
const nextPort = Number(process.env.E2E_NEXT_PORT ?? 3765);
const apiUrl = `http://127.0.0.1:${djangoPort}/api`;
const secretKey = "e2e-secret-key";
const readOnlySecretKey = "e2e-read-only-secret-key";
const withNext = process.argv.includes("--next");

const servers = [];

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", ...options, env: { ...process.env, ...options.env } });
    child.on("error", reject);
    child.on("exit", (code) =>
      code === 0 ? resolve() : reject(new Error(`${command} ${args.join(" ")} exited with ${code}`)),
    );
  });
}

function start(command, args, options = {}) {
  const child = spawn(command, args, { stdio: "inherit", ...options, env: { ...process.env, ...options.env } });
  servers.push(child);
  return child;
}

async function waitFor(url, child) {
  for (let attempt = 0; attempt < 120; attempt++) {
    if (child.exitCode !== null) {
      throw new Error(`The server of ${url} exited with ${child.exitCode}`);
    }
    try {
      // Any answer means the server is up, also 401 or 403
      await fetch(url);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`${url} did not answer in time`);
}

async function main() {
  const workDir = await mkdtemp(join(tmpdir(), "django-headless-e2e-"));
  const djangoEnv = { E2E_DATABASE: join(workDir, "db.sqlite3"), PYTHONUNBUFFERED: "1" };

  try {
    await run(python, ["manage.py", "migrate", "--run-syncdb", "-v", "0"], { cwd: djangoDir, env: djangoEnv });
    await run(python, ["manage.py", "loaddata", "blog", "-v", "0"], { cwd: djangoDir, env: djangoEnv });

    const django = start(python, ["manage.py", "runserver", `127.0.0.1:${djangoPort}`, "--noreload"], {
      cwd: djangoDir,
      env: djangoEnv,
    });
    await waitFor(`${apiUrl}/schema`, django);

    const cli = join(clientDir, "dist", "cli.js");
    await run("node", [cli, "generate", "--url", `${apiUrl}/schema`, "--out", "e2e/generated/headless.ts"], {
      cwd: clientDir,
      env: { DJANGO_HEADLESS_SECRET_KEY: secretKey },
    });
    await run(
      "node",
      [cli, "generate", "--url", `${apiUrl}/schema`, "--secret-key", readOnlySecretKey, "--out", "e2e/generated/read-only.ts"],
      { cwd: clientDir },
    );

    await run("npx", ["tsc", "-p", "e2e/tsconfig.json"], { cwd: clientDir });
    await run("npx", ["vitest", "run", "--config", "e2e/vitest.config.ts"], {
      cwd: clientDir,
      env: { E2E_API_URL: apiUrl, E2E_SECRET_KEY: secretKey, E2E_READ_ONLY_SECRET_KEY: readOnlySecretKey },
    });

    if (withNext) {
      await testNext(workDir);
    }
  } finally {
    for (const server of servers) {
      server.kill();
    }
    await rm(workDir, { recursive: true, force: true });
  }
}

async function testNext(workDir) {
  // Install the package as a user would: from the packed tarball
  await run("npm", ["pack", "--pack-destination", workDir], { cwd: clientDir });
  const tarball = (await readdir(workDir)).find((name) => name.endsWith(".tgz"));

  await run("npm", ["ci"], { cwd: nextDir });
  await run("npm", ["install", "--no-save", join(workDir, tarball)], { cwd: nextDir });

  // The package is ESM only; Node.js 22 loads it with require() as well
  await run(
    "node",
    ["-e", 'const { DjangoRestClient } = require("@django-headless/client"); new DjangoRestClient({ baseUrl: "/api" });'],
    { cwd: nextDir },
  );
  await run("node", [join(clientDir, "dist", "cli.js"), "generate", "--url", `${apiUrl}/schema`, "--out", "headless.ts"], {
    cwd: nextDir,
    env: { DJANGO_HEADLESS_SECRET_KEY: secretKey },
  });

  const nextEnv = { API_URL: apiUrl, API_SECRET_KEY: secretKey, NEXT_TELEMETRY_DISABLED: "1" };
  // The binary itself, not npx, so stopping the process stops the server
  const nextBin = join(nextDir, "node_modules", ".bin", "next");
  await run(nextBin, ["build"], { cwd: nextDir, env: nextEnv });

  const next = start(nextBin, ["start", "--port", String(nextPort)], { cwd: nextDir, env: nextEnv });
  const nextUrl = `http://127.0.0.1:${nextPort}`;
  await waitFor(nextUrl, next);

  // The page is rendered at build time; the edge route on each request
  const page = await (await fetch(nextUrl)).text();
  expectIncludes(page, "Getting started with Django", "the static page");
  expectIncludes(page, "The Django blog", "the static page");

  const edge = await fetch(`${nextUrl}/edge`);
  const body = await edge.json();
  if (edge.status !== 200 || body.runtime !== "edge" || body.title !== "Getting started with Django") {
    throw new Error(`The edge route answered ${edge.status} ${JSON.stringify(body)}`);
  }
  console.log("Next.js: the static page and the edge route work with the client");
}

function expectIncludes(text, expected, name) {
  if (!text.includes(expected)) {
    throw new Error(`${name} does not include "${expected}"`);
  }
}

main().catch((error) => {
  console.error(error);
  for (const server of servers) {
    server.kill();
  }
  process.exit(1);
});
