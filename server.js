
const { spawn } = require("child_process");
const path = require("path");

const python = process.env.PYTHON ||
    (process.platform === "win32" ? "python" : "python3");

const script = path.join(__dirname, "api.py");

console.log("======================================");
console.log("     PRITESH AI NEXT GEN");
console.log("     DUAL PREDICTION ENGINE");
console.log("======================================");
console.log("Starting Python API Engine...");

const child = spawn(python, [script], {
    stdio: "inherit",
    cwd: __dirname
});

child.on("error", (err) => {
    console.error("ENGINE START ERROR:", err.message);
    console.log("Run api.py directly using Pydroid 3.");
    process.exitCode = 1;
});

child.on("exit", (code, signal) => {
    if (signal) {
        console.log("Engine stopped:", signal);
    } else {
        console.log("Engine exited with code:", code);
    }
    process.exitCode = code ?? 0;
});

["SIGINT", "SIGTERM"].forEach((signal) => {
    process.on(signal, () => {
        child.kill(signal);
    });
});
