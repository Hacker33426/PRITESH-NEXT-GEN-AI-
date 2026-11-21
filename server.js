
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const ROOT = __dirname;

console.log("\n==================================");
console.log("     PRITESH AI NEXT GEN");
console.log("     PYTHON ENGINE LAUNCHER");
console.log("==================================\n");

const possibleFiles = [
    process.env.PYTHON_FILE,
    path.join(ROOT, "api.py"),
    path.join(ROOT, "backend", "api.py"),
    path.join(ROOT, "src", "api.py"),
    path.join(ROOT, "python", "api.py")
].filter(Boolean);

const apiFile = possibleFiles.find(file => fs.existsSync(file));

if (!apiFile) {
    console.error("[ERROR] api.py file not found!");
    console.error("\nSearched locations:");

    possibleFiles.forEach(file => {
        console.error(" - " + file);
    });

    console.error("\nPut api.py in the same folder as server.js.");
    process.exit(1);
}

console.log("[OK] Python file:", apiFile);

const candidates = process.env.PYTHON
    ? [process.env.PYTHON]
    : process.platform === "win32"
        ? ["python", "py"]
        : ["python3", "python"];

let selectedPython = null;

for (const cmd of candidates) {
    const args = cmd === "py" ? ["-3", "--version"] : ["--version"];

    const check = spawnSync(cmd, args, {
        encoding: "utf8",
        timeout: 5000
    });

    if (!check.error && check.status === 0) {
        selectedPython = cmd;
        break;
    }
}

if (!selectedPython) {
    console.error("[ERROR] Python not detected!");
    console.error("Install Python or configure the PYTHON variable.");
    console.error("On Pydroid 3, open and run api.py directly.");
    process.exit(1);
}

console.log("[OK] Python:", selectedPython);
console.log("[START] Starting engine...\n");

const args = selectedPython === "py"
    ? ["-3", apiFile]
    : [apiFile];

const child = spawn(selectedPython, args, {
    cwd: path.dirname(apiFile),
    stdio: "inherit",
    windowsHide: true
});

child.on("error", error => {
    console.error("[START ERROR]", error.message);
    process.exitCode = 1;
});

child.on("exit", code => {
    console.log("\n[ENGINE STOPPED] Exit code:", code);
    process.exitCode = code ?? 1;
});

process.on("SIGINT", () => {
    child.kill("SIGINT");
});
