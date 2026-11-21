
const http = require("http");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const PORT = process.env.PORT || 3000;
const PYTHON_FILE = path.join(__dirname, "PRITESH AI.py");

let pythonProcess = null;

function startPython() {
    if (pythonProcess) return;

    if (!fs.existsSync(PYTHON_FILE)) {
        console.error("[ERROR] PRITESH AI.py not found!");
        return;
    }

    const python = process.env.PYTHON || "python3";

    pythonProcess = spawn(python, [PYTHON_FILE], {
        cwd: __dirname,
        env: {
            ...process.env,
            PORT: "8000"
        },
        stdio: ["ignore", "inherit", "inherit"]
    });

    pythonProcess.on("error", err => {
        console.error("[PYTHON ERROR]", err.message);
        pythonProcess = null;
    });

    pythonProcess.on("exit", code => {
        console.log("[PYTHON EXIT]", code);
        pythonProcess = null;
    });
}

const server = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");

    if (req.url === "/") {
        res.end(JSON.stringify({
            name: "PRITESH AI NEXT GEN",
            status: "ONLINE",
            python: "PRITESH AI.py",
            engine: pythonProcess ? "RUNNING" : "STOPPED"
        }));
        return;
    }

    const target = "http://127.0.0.1:8000" + req.url;

    fetch(target)
        .then(async response => {
            res.writeHead(response.status, {
                "Content-Type":
                    response.headers.get("content-type") ||
                    "application/json"
            });
            res.end(await response.text());
        })
        .catch(error => {
            res.writeHead(503);
            res.end(JSON.stringify({
                error: "Python backend unavailable",
                details: error.message
            }));
        });
});

server.listen(PORT, "0.0.0.0", () => {
    console.log("================================");
    console.log(" PRITESH AI NEXT GEN");
    console.log(" SERVER STARTED");
    console.log(" PORT:", PORT);
    console.log("================================");

    startPython();
});
