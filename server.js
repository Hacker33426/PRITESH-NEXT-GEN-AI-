
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const ROOT = __dirname;
const IGNORE = new Set([
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv"
]);

console.log("\n==================================");
console.log("      PRITESH AI NEXT GEN");
console.log("      AUTO FILE FINDER");
console.log("==================================\n");

function findApiPy(folder, depth = 0) {
    if (depth > 8) return null;

    let entries;

    try {
        entries = fs.readdirSync(folder, {
            withFileTypes: true
        });
    } catch {
        return null;
    }

    // First check files in this folder
    for (const entry of entries) {
        if (
            entry.isFile() &&
            entry.name.toLowerCase() === "api.py"
        ) {
            return path.join(folder, entry.name);
        }
    }

    // Then search subfolders
    for (const entry of entries) {
        if (
            entry.isDirectory() &&
            !IGNORE.has(entry.name)
        ) {
            const result = findApiPy(
                path.join(folder, entry.name),
                depth + 1
            );

            if (result) return result;
        }
    }

    return null;
}

console.log("[SEARCH] Searching for api.py...");
console.log("[ROOT]", ROOT);

const apiFile = process.env.PYTHON_FILE
    ? path.resolve(ROOT, process.env.PYTHON_FILE)
    : findApiPy(ROOT);

if (!apiFile || !fs.existsSync(apiFile)) {
    console.error("\n[ERROR] api.py not found!");
    console.error("Search completed inside:", ROOT);
    console.error("\nCheck that the filename is exactly api.py");
    console.error("Not api.py.txt or API.txt");
    console.error("\nIf it is in another location, set PYTHON_FILE.");
    process.exit(1);
}

console.log("\n[SUCCESS] api.py found!");
console.log("[PATH]", apiFile);

// Find Python
const candidates = process.env.PYTHON
    ? [process.env.PYTHON]
    : process.platform === "win32"
        ? ["python", "py"]
        : ["python3", "python"];

let python = null;

for (const cmd of candidates) {
    const args = cmd === "py"
        ? ["-3", "--version"]
        : ["--version"];

    const check = spawnSync(cmd, args, {
        encoding: "utf8",
        timeout: 5000
    });

    if (!check.error && check.status === 0) {
        python = cmd;
        break;
    }
}

if (!python) {
    console.error("\n[ERROR] Python not detected!");
    console.error("Run api.py directly in Pydroid 3,");
    console.error("or configure the PYTHON environment variable.");
    process.exit(1);
}

console.log("[OK] Python:", python);
console.log("[START] Starting prediction engine...\n");

const pythonArgs = python === "py"
    ? ["-3", apiFile]
    : [apiFile];

const child = spawn(python, pythonArgs, {
    cwd: path.dirname(apiFile),
    stdio: "inherit",
    windowsHide: true
});

child.on("error", error => {
    console.error("\n[ENGINE ERROR]", error.message);
});

child.on("exit", code => {
    console.log("\n[ENGINE STOPPED] Exit code:", code);
    process.exitCode = code ?? 1;
});

process.on("SIGINT", () => {
    child.kill("SIGINT");
});
