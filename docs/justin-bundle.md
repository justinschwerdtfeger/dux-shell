# Justin's stable DMS bundle

This pipeline ships only from `justinschwerdtfeger/dux-shell:justin-stable`.
It is separate from `release.yml`, `dms-stable.yml`, `point-release.yml`, and
`port.yml`. Do not dispatch those upstream-oriented workflows for this image.
The new workflow is disabled until repository variable `JUSTIN_DMS_ENABLED`
is exactly `true`. Nothing in this change activates remote automation.

## Release policy

- Daily at 07:17 UTC, or a manual **Justin stable bundle** run with `sync=true`,
  read the upstream public releases API and select the highest numeric `vX.Y.Z`
  release that is neither draft nor prerelease. Unrelated tags and `-rc` tags
  are excluded. Fetch that exact release tag, never upstream master.
- Start from the fork's shipping branch. Merge the new release, keeping fork
  patches. Keep the fork's `.github/` configuration during merges so upstream
  automation is never imported or enabled by the sync. The stable record is
  `.github/justin/upstream-stable.json` and records the tag and resolved commit.
  Reject rollback, moved tags, and non-descendant upstream release history.
- A push to `justin-stable`, or dispatch with `sync=false`, tests and ships that
  branch without an upstream API request/fetch. Pushes to development branches
  do not publish bundles. A dispatch can run from `master` or `justin-stable`;
  it always checks out `justin-stable`.
- Initialize submodules at their gitlinks, including `dux-qml-common`. Do not
  use `git submodule update --remote`. The `quickshell/DCommon` symlink must
  resolve before building. `setup-go` reads the candidate's `core/go.mod`
  (currently Go 1.27.1); the QML tests use the candidate's Nix environment.
- Run automation tests, Go race tests, and existing offscreen QML/JS unit tests,
  then `make -C core dist ARCH=amd64 DIST_OSES=linux`. This embeds backend and UI
  with `distro_binary withshell`, including the pinned DCommon, and disables the
  builtin updater. No separate source-tree runtime installation is needed.

The archive is `dms-justin-<full-fork-commit>-linux-amd64.tar.gz`. A release named
`justin-<full-fork-commit>` contains that archive, `SHA256SUMS`, and `metadata.json`
(fork commit, upstream stable tag/commit, submodule commit, archive SHA256).
Timestamps come from the commit and archive modes are preserved. The bundle
installs `/usr/bin/dms`, the system user unit, three desktop entries, the icon,
and the project license.
It deliberately avoids root `make install`, which installs the unit into the
build user's home. Completions are optional and omitted.

Only after local verification does publication push the commit-named tag to
Justin's fork, create/upload a draft, download and verify its assets, advance
`justin-stable` with a normal fast-forward push, and publish the release as latest.
A published release is reused only if checksums match; its assets are never
overwritten. A partial draft can be retried. No moving release/tag is used by
the image. Enable GitHub's immutable releases for additional server enforcement
if desired; the workflow does not change repository settings.

Conflicts, test/build failures, stale branch heads, or dependency problems fail
Actions without issues, comments, or PRs. Before publication, failures leave the
previous published release intact. An asset-upload failure may leave a tag/draft;
a final release API failure may leave a tested shipping commit with the previous
release still published. Retry the workflow to finish; no force push is used.
On conflict, manually resolve the upstream merge in the fork and update the record,
then push `justin-stable` for verification. A race after uploading assets can
leave a draft; it does not publish an obsolete candidate.

## Activation and bootstrap (future, explicitly authorized operations)

The local `justin-stable` branch currently preserves the development history
where this implementation was prepared. It is not yet based on a reviewed
upstream stable release. Preserve this implementation on a backup branch before
reconstructing `justin-stable` from stable; do not merge development master into
the shipping branch. The checked-in record contains null values and intentionally
fails validation until bootstrapped. No release URL or checksum in this
implementation refers to a claimed existing asset.

1. Review and commit the implementation in Justin's fork when authorized. Put
   `justin-bundle.yml` on default branch `master` for scheduled runs. Keep
   `JUSTIN_DMS_ENABLED` unset while bootstrapping. Do not run the upstream-style
   release/port workflows or provision their GitHub App/satellite repo secrets.
2. Once upstream reads are authorized, choose a published, non-prerelease stable
   `vX.Y.Z` release. Fetch only that tag from
   `https://github.com/duxlabs-dev/dux-shell.git`, record its peeled commit, and
   preserve the current branch as `justin-stable-development-backup`, then
   recreate `justin-stable` at that commit. Cherry-pick only Justin's intended
   feature patches, then bring the reviewed fork `.github/`
   configuration, the three `scripts/justin-*` scripts, `scripts/test_justin_stable.py`,
   and this document from the implementation commit onto it. Do not merge
   development master as a shortcut. With `origin` confirmed as Justin's fork,
   the future preparation commands are below. Commit all intended local changes
   first; the clean-tree check and non-forcing branch rename protect the existing
   work. These steps assume `justin-stable` has not been published; if it has,
   coordinate the branch replacement separately without force-pushing it.

   ```sh
   : "${STABLE_TAG:?Set the reviewed published stable vX.Y.Z tag}"
   : "${AUTOMATION_COMMIT:?Set the reviewed implementation commit}"
   test -z "$(git status --porcelain)"
   git fetch --no-tags https://github.com/duxlabs-dev/dux-shell.git "refs/tags/$STABLE_TAG"
   UPSTREAM_COMMIT=$(git rev-parse 'FETCH_HEAD^{commit}')
   git switch justin-stable
   git branch -m justin-stable-development-backup
   git switch -c justin-stable "$UPSTREAM_COMMIT"
   # Cherry-pick the intended fork feature commits here, before restoring files.
   git restore --source="$AUTOMATION_COMMIT" --staged --worktree -- \
     .github scripts/justin-stable.py scripts/justin-bundle.sh \
     scripts/justin-publish.sh scripts/test_justin_stable.py docs/justin-bundle.md
   python3 - "$STABLE_TAG" "$UPSTREAM_COMMIT" <<'PY'
   import json
   from pathlib import Path
   import sys
   Path('.github/justin/upstream-stable.json').write_text(
       json.dumps({'tag': sys.argv[1], 'commit': sys.argv[2]}, indent=2) + '\n')
   PY
   git add .github/justin/upstream-stable.json
   git submodule update --init --recursive
   python3 scripts/justin-stable.py
   ```
3. Set `.github/justin/upstream-stable.json` to
   `{"tag":"<chosen stable vX.Y.Z>","commit":"<actual peeled 40-character commit>"}`.
   Verify that this stable base supports `distro_binary withshell`, the pinned
   DCommon submodule, the existing test entry points and the asset paths used by
   `justin-bundle.sh`. An older stable without these needs a reviewed port of the
   packaging/embed changes or a later suitable stable; copying all of master is
   not a substitute. Run the checks before committing and pushing the branch.
4. Enable Actions in the fork; set `JUSTIN_DMS_ENABLED=true`. Allow the workflow's
   `GITHUB_TOKEN` `contents:write` on this fork's tags/releases and shipping branch.
   No PAT, GitHub App or cross-repository secret is needed. Branch protection
   that blocks bot pushes causes a safe failure and must be reconciled with the
   desired direct-promotion policy. Dispatch **Justin stable bundle**, initially
   with `sync=false`; inspect tests, metadata, checksums and published assets.
5. Activate image consumption using `DMS-FORK.md` in `justin-bazzite-dx` after
   that first real release exists. Subsequent daily sync checks read upstream;
   they never push upstream or create PRs/issues/comments anywhere.

Scheduled workflows run from the default branch. Keep this workflow and helper
changes coordinated on `master` and `justin-stable`. Upstream `.github/` updates
are deliberately excluded; review CI changes separately on the fork. Changes to
other workflow files in shipping commits may require manual publication with
appropriately authorized workflow permissions; no broad credential is stored by
this pipeline to bypass GitHub's workflow-file restrictions.

The image independently polls only successful **published fork bundles** on its
daily build and dispatch, commits the exact release/hash in its own repository,
and builds that exact commit in the same run. This accounts for
[GitHub's token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow):
bot pushes/releases do not start ordinary downstream push/release workflows.

All additions run in CI or during image construction. No client updater, timer,
background process, extra idle CPU, or retained runtime memory is introduced.
