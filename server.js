
const express = require("express");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const PYTHON_FILE = path.join(__dirname, "PRITESH AI.py");

if (!fs.existsSync(PYTHON_FILE)) {
    console.error("[ERROR] PRITESH AI.py not found!");
    console.error("Place PRITESH AI.py in the same folder as server.js");
    process.exit(1);
}

const PYTHON = process.env.PYTHON || "python";

let pythonProcess = null;
let pythonOutput = "";
let pythonError = "";
let started = false;

function startPython() {
    if (started) return;
    started = true;

    console.log("[PRITESH AI] Starting Python engine...");

    pythonProcess = spawn(PYTHON, [PYTHON_FILE], {
        cwd: __dirname,
        env: { ...process.env, PORT: "8000" },
        stdio: ["ignore", "pipe", "pipe"]
    });

    pythonProcess.stdout.on("data", data => {
        pythonOutput += data.toString();
        console.log("[PYTHON]", data.toString().trim());
    });

    pythonProcess.stderr.on("data", data => {
        pythonError += data.toString();
        console.error("[PYTHON ERROR]", data.toString().trim());
    });

    pythonProcess.on("error", error => {
        console.error("[ERROR] Python launch failed:", error.message);
        started = false;
    });

    pythonProcess.on("exit", code => {
        console.log("[PRITESH AI] Python stopped:", code);
        started = false;
        pythonProcess = null;
    });
}

app.get("/", (req, res) => {
    res.json({
        name: "PRITESH AI NEXT GEN",
        status: "ONLINE",
        python_file: "PRITESH AI.py",
        engine: started ? "RUNNING" : "STOPPED"
    });
});

app.get("/status", async (req, res) => {
    try {
        const response = await fetch("http://127.0.0.1:8000/api/status");
        const data = await response.json();
        res.json(data);
    } catch (error) {
        res.status(503).json({
            status: "STARTING",
            message: "Python API is not responding yet"
        });
    }
});

app.get("/api/*path", async (req, res) => {
    try {
        const target = "http://127.0.0.1:8000" + req.originalUrl;
        const response = await fetch(target);
        const data = await response.text();

        res.status(response.status);
        res.type(response.headers.get("content-type") || "application/json");
        res.send(data);
    } catch (error) {
        res.status(503).json({
            error: "Python backend unavailable",
            details: error.message
        });
    }
});

app.listen(PORT, "0.0.0.0", () => {
    console.log("----------------------------------");
    console.log("  PRITESH AI NEXT GEN");
    console.log("  30S WINGO ENGINE");
    console.log("----------------------------------");
    console.log("Server: http://localhost:" + PORT);

    startPython();
});

process.on("SIGINT", () => {
    if (pythonProcess) pythonProcess.kill();
    process.exit(0);
});

process.on("SIGTERM", () => {
    if (pythonProcess) pythonProcess.kill();
    process.exit(0);
});
