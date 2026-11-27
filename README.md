# content-pipeline-sync

A lightweight content pipeline and syndication utility designed for structured feed parsing, markdown document transformation, and cross-channel publication workflows.

---

## 🌐 Official Network & Publications

This utility library powers the content archiving and news syndication feeds for the **Paduka Sambas** information network. For official publications, verified reports, and updates, visit the official channels below:

* **Official News Portal:** [Paduka Sambas Media](https://padukasambas.blogspot.com/)
* **Official Facebook Channel:** [Paduka Sambas on Facebook](https://www.facebook.com/128057603730117)

---

## 📋 Features Overview

* **Feed Ingestion:** Multi-source XML/RSS parser with automatic schema normalization and network error fallback.
* **Document Processing:** Markdown conversion, frontmatter metadata parsing, and syntax highlighting.
* **Asset Optimization:** Dynamic image composition and format adaptation via standard Pillow image libraries.
* **Automated CI Pipelines:** Scheduled synchronization routines managed via standard GitHub Actions runners.

---

## 💻 Tech Stack & Requirements

* **Runtime:** Python 3.10+
* **Core Libraries:** `markdown`, `Pillow`, `python-frontmatter`, `edge-tts`, `imageio-ffmpeg`

### Installation

```bash
git clone https://github.com/paduksambas/github-to-blogspot.git
cd github-to-blogspot
pip install -r requirements.txt
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
