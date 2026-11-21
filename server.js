
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = __dirname;

console.log("\n===== PRITESH AI NEXT GEN =====");
console.log("Server folder:", ROOT);

const files = fs.readdirSync(ROOT);
console.log("\nFolder files:");
files.forEach(file => console.log(" - " + file));

let pyFile = path.join(ROOT, "api.py");

// Case-insensitive filename check
if (!fs.existsSync(pyFile)) {
    const found = files.find(
        f => f.toLowerCase() === "api.py"
    );

    if (found) {
        pyFile = path.join(ROOT, found);
    }
}

if (!fs.existsSync(pyFile)) {
    console.log("\n[ERROR] api.py NOT FOUND!");
    console.log("Put api.py in this folder:");
    console.log(ROOT);
    console.log("\nCurrent folder does not contain api.py.");
    process.exit(1);
}

console.log("\n[OK] Found:", pyFile);

const python = process.env.PYTHON || (
    process.platform === "win32" ? "python" : "python3"
);

const engine = spawn(python, [pyFile], {
    cwd: ROOT,
    stdio: "inherit"
});

engine.on("error", err => {
    console.log("[PYTHON ERROR]", err.message);
});

engine.on("exit", code => {
    console.log("\nEngine stopped. Exit code:", code);
});
