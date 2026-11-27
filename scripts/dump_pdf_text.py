import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
OUTPUT_DIR = ROOT / "data" / "raw"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(IMAGES_DIR.glob("*.pdf")):
        target = OUTPUT_DIR / f"{pdf.stem}.txt"
        subprocess.run(["pdftotext", "-layout", str(pdf), str(target)], check=True)
        raw_target = OUTPUT_DIR / f"{pdf.stem}-raw.txt"
        subprocess.run(["pdftotext", "-raw", str(pdf), str(raw_target)], check=True)
        print(
            f"{pdf.name} -> {target.relative_to(ROOT)}, {raw_target.relative_to(ROOT)}"
        )


if __name__ == "__main__":
    main()
