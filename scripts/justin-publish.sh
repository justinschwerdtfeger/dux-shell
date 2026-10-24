#!/usr/bin/env bash
set -euo pipefail

test "${GITHUB_REPOSITORY:?}" = justinschwerdtfeger/dux-shell
export GH_REPO=justinschwerdtfeger/dux-shell
sha=$(git rev-parse HEAD)
tag="justin-$sha"
output=$(realpath "${1:?Usage: justin-publish.sh BUNDLE_DIRECTORY}")
archive="dms-$tag-linux-amd64.tar.gz"
cd "$output"
sha256sum --check SHA256SUMS

# Never promote an obsolete candidate over a newer shipping-branch push.
git -C "$GITHUB_WORKSPACE" fetch --no-tags origin justin-stable
remote=$(git -C "$GITHUB_WORKSPACE" rev-parse FETCH_HEAD)
test "$remote" = "$BASE_SHA" || test "$remote" = "$sha"
if git -C "$GITHUB_WORKSPACE" show-ref --verify --quiet "refs/tags/$tag"; then
    test "$(git -C "$GITHUB_WORKSPACE" rev-parse "$tag^{commit}")" = "$sha"
fi
# Make the tested merge commit addressable before the release API creates its draft.
git -C "$GITHUB_WORKSPACE" push origin "HEAD:refs/tags/$tag"

# Query the list so authentication/API failures cannot be mistaken for a missing release.
gh api --paginate "repos/$GH_REPO/releases?per_page=100" --jq '.[]' | jq -s \
    --arg tag "$tag" 'map(select(.tag_name == $tag)) | first // null' > release.json
if [[ $(jq -r '.draft' release.json) == false ]]; then
    verify=$(mktemp -d)
    trap 'rm -rf "$verify"' EXIT
    gh release download "$tag" --dir "$verify" --pattern "$archive" --pattern metadata.json --pattern SHA256SUMS
    cmp SHA256SUMS "$verify/SHA256SUMS"
    (cd "$verify" && sha256sum --check SHA256SUMS)
else
    if [[ $(cat release.json) == null ]]; then
        gh release create "$tag" --verify-tag --draft --title "Justin DMS $sha" \
            --notes "Embedded Linux amd64 distribution bundle from justin-stable. See metadata.json for upstream stable provenance."
    fi
    gh release upload "$tag" "$archive" metadata.json SHA256SUMS --clobber
    verify=$(mktemp -d)
    trap 'rm -rf "$verify"' EXIT
    gh release download "$tag" --dir "$verify" --pattern "$archive" --pattern metadata.json --pattern SHA256SUMS
    cmp SHA256SUMS "$verify/SHA256SUMS"
    (cd "$verify" && sha256sum --check SHA256SUMS)
fi

# A normal fast-forward push fails safely if another writer advanced the branch.
git -C "$GITHUB_WORKSPACE" push origin HEAD:refs/heads/justin-stable
if [[ $(jq -r '.draft' release.json) != false ]]; then
    gh release edit "$tag" --draft=false --latest
fi
