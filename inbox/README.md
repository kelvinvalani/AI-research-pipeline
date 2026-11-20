# Research Inbox (`inbox/`)

Drop any papers (`.pdf`, `.tex`, `.bib`), whiteboard/iPad photos (`.png`, `.jpg`), Jupyter notebooks (`.ipynb`), or data files here **before** creating a project — or whenever you want to hand reference files to the agent quickly.

## How the Agent Handles Files Here
1. Mention the file(s) in chat (e.g., *"Look at `inbox/paper.pdf`, Section 3 & Eq. (14) — let's test..."*).
2. During Stage 1 (`01-idea-to-spec`), the agent inspects the file, scaffolds (or locates) the target project under `projects/<project>/`, **moves** the file into `projects/<project>/refs/`, and records the exact path and equation/page anchors in `lead.yaml` and `notes/01_background.md`.
3. `inbox/` stays empty between ideas so unrelated projects never pile up here.
