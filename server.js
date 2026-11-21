
"use strict";

const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const APP = "PRITESH AI NEXT GEN";
const ROOT = __dirname;
const PY_FILE = path.join(ROOT, "api.py");

console.log("\n====================================");
console.log("       " + APP);
console.log("       SERVER TROUBLESHOOTING");
console.log("====================================\n");

// 1. Check Python file
if (!fs.existsSync(PY_FILE)) {
    console.error("[ERROR] api.py missing!");
    console.error("Place api.py and server.js in the same folder.");
    process.exit(1);
}

// 2. Detect Python
const candidates = process.env.PYTHON
    ? [{ cmd: process.env.PYTHON, args: [] }]
    : process.platform === "win32"
        ? [
            { cmd: "python", args: [] },
            { cmd: "py", args: ["-3"] }
          ]
        : [
            { cmd: "python3", args: [] },
            { cmd: "python", args: [] }
          ];

let selected = null;

for (const item of candidates) {
    const check = spawnSync(
        item.cmd,
        [...item.args, "--version"],
        { encoding: "utf8", timeout: 5000 }
    );

    if (!check.error && check.status === 0) {
        selected = item;
        break;
    }
}

if (!selected) {
    console.error("[ERROR] Python not detected!");
    console.error("Install Python or set PYTHON environment variable.");
    console.error("Pydroid 3 users can run api.py directly.");
    process.exit(1);
}

console.log("[OK] Python detected:", selected.cmd);
console.log("[OK] Python file:", PY_FILE);
console.log("[START] Launching prediction engine...\n");

// 3. Start engine
let stopping = false;

const engine = spawn(
    selected.cmd,
    [...selected.args, PY_FILE],
    {
        cwd: ROOT,
        stdio: "inherit",
        windowsHide: true
    }
);

// 4. Handle startup errors
engine.on("error", (err) => {
    console.error("\n[ENGINE ERROR]", err.message);
    console.error("Check Python installation and file permissions.");
    process.exitCode = 1;
});

// 5. Handle engine exit
engine.on("exit", (code, signal) => {
    if (signal) {
        console.log("\n[STOPPED] Signal:", signal);
    } else {
        console.log("\n[EXIT] Python exit code:", code);
    }

    if (!stopping && code !== 0) {
        console.error("[WARNING] Engine stopped unexpectedly.");
    }

    process.exitCode = code ?? 1;
});

// 6. Safe shutdown
function shutdown(signal) {
    if (stopping) return;

    stopping = true;
    console.log("\n[SHUTDOWN] Stopping engine...");

    if (engine.exitCode === null && !engine.killed) {
        engine.kill(signal);
    }
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

console.log("[OK] Server launcher initialized.");
