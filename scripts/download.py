"""Download the NHS England RTT full CSV extract named in config.yaml (not committed: ~83 MB)."""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rtt.load import load_config  # noqa: E402


def main():
    cfg = load_config()
    dest = Path(cfg["raw_csv"])
    if dest.exists():
        print(f"already present: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(cfg["download_url"], headers={"User-Agent": "nhs-rtt-benchmarking"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        assert len(csvs) == 1, csvs
        dest.write_bytes(z.read(csvs[0]))
    print(f"saved {dest} ({dest.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
