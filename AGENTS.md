# Working Rules

1. Follow `BUILD_INSTRUCTIONS.md` phase by phase. Verify acceptance criteria before moving on. Make one local git commit per phase.
2. Never run `sudo` yourself. When a step needs it, write the exact commands and ask the human to run them, then continue.
3. Never invent secrets. The Roboflow API key is supplied by the human in `.env`. Never commit `.env`, videos, model weights, `node_modules`, `venv`, or `data/`.
4. Do not assume a GPU. Detect the device at runtime (CUDA if available, else CPU) and log which one was used. The machine has an NVIDIA MX350 (2 GB VRAM) and CUDA may not work; do not spend time on CUDA setup beyond a quick check.
5. Python: venv + pip + `requirements*.txt` only (no Poetry, no conda). Postgres and Redis run natively on Ubuntu 24 (no Docker).
6. Everything the dashboard shows must come from the results schema in Section 7. Keep the pipeline behind the interface in Section 8.
7. If blocked after two honest attempts, stop and report what you tried; do not hack around it or silently change scope.
8. At the end of each phase, report: what was built, how you verified it, anything deferred, and any decision the human must make.
