#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
output=$(realpath -m "${1:?Usage: justin-bundle.sh OUTPUT_DIRECTORY}")
sha=$(git rev-parse HEAD)
tag="justin-$sha"
epoch=$(git show -s --format=%ct HEAD)
submodule=$(git ls-tree HEAD dux-qml-common | awk '{print $3}')
test "$submodule" = "$(git -C dux-qml-common rev-parse HEAD)"
test -f quickshell/DCommon/Widgets/DIcon.qml
test -x core/bin/dms-linux-amd64
mkdir -p "$output"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

install -Dm755 core/bin/dms-linux-amd64 "$stage/usr/bin/dms"
install -Dm644 assets/systemd/dms.service "$stage/usr/lib/systemd/user/dms.service"
for desktop in dms-open dev.duxlabs.shell dev.duxlabs.shell.notepad; do
    install -Dm644 "assets/$desktop.desktop" "$stage/usr/share/applications/$desktop.desktop"
done
install -Dm644 assets/dev.duxlabs.shell.svg "$stage/usr/share/icons/hicolor/scalable/apps/dev.duxlabs.shell.svg"
install -Dm644 LICENSE "$stage/usr/share/licenses/dms/LICENSE"

archive="dms-$tag-linux-amd64.tar.gz"
tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner \
    -C "$stage" -cf - usr | gzip -n > "$output/$archive"
python3 - "$output" "$archive" "$sha" "$submodule" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

output, archive, sha, submodule = sys.argv[1:]
metadata = {
    "schema": 1,
    "repository": "justinschwerdtfeger/dux-shell",
    "branch": "justin-stable",
    "commit": sha,
    "release": "justin-" + sha,
    "upstream": json.loads(Path(".github/justin/upstream-stable.json").read_text()),
    "dux_qml_common": submodule,
    "platform": "linux-amd64",
    "archive": archive,
    "sha256": hashlib.sha256((Path(output) / archive).read_bytes()).hexdigest(),
}
(Path(output) / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
PY
(cd "$output" && sha256sum "$archive" metadata.json > SHA256SUMS)
