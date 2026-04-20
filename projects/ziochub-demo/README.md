## ZIoCHub Static Demo (client-only)

This folder is a **static-site demo** of the ZIoCHub client UI with **fake/lab data**.

### What you get
- A self-contained site under `demo/ziochub-demo/site/`
- Prebuilt datasets (IOCs, campaigns, YARA, analysts) under `demo/ziochub-demo/site/data/`
- Everything runs **client-side only** (HTML/CSS/JS). No Flask/SQLite required.

### Build the demo dataset/site
The builder reads lab inputs from the repo and writes a static demo site.

Inputs (in this repo):
- `users/users.json` (+ avatars in `users/*.jpg|png|...`)
- `indicators/*.txt` (IOC lines)
- `indicators/campains.txt` (campaign definitions)
- `indicators/*.yar` (sample YARA rules)

Run:

```bash
python demo/ziochub-demo/build_demo.py
```

Output:
- `demo/ziochub-demo/site/index.html`
- `demo/ziochub-demo/site/data/*.json`
- `demo/ziochub-demo/site/assets/avatars/*`
- `demo/ziochub-demo/site/assets/yara/*`

### Serve locally (example)
Any static server works.

```bash
python -m http.server 8000 --directory demo/ziochub-demo/site
```

Then open `http://localhost:8000`.

