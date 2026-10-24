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

## Stable base and activation

`justin-stable` is based on published upstream `v2.0.0`, commit
`9b413296b16721f7679fb62e624cb1ed2433fa58`, plus Justin's widget-inset
feature and the bundle automation. Its submodule stays at the release's pinned
commit. The stable record is populated and passes local ancestry validation.
The former development-based branch is preserved locally as
`justin-stable-development-backup` at `617e7237809b4a6fe1b2d637732380281a046dc0`.
No development master merge is needed.

The old development-based `justin-stable` was already published to Justin's fork
at that same backup commit. The corrected branch intentionally has different
history. The following publication and activation steps have not been performed:

1. Keep `JUSTIN_DMS_ENABLED` unset or false while publishing. Preserve the old
   branch remotely, then replace only Justin's shipping branch with an explicit
   lease. Confirm `origin` is Justin's fork first. If the remote branch has
   advanced beyond the known old commit, the lease must fail; inspect those
   changes instead of removing the lease or overwriting them.

   ```sh
   git remote get-url origin
   git push origin refs/heads/justin-stable-development-backup:refs/heads/justin-stable-development-backup
   git push --force-with-lease=refs/heads/justin-stable:617e7237809b4a6fe1b2d637732380281a046dc0 \
     origin refs/heads/justin-stable:refs/heads/justin-stable
   ```

2. For scheduled runs, set the fork's default branch to `justin-stable` in
   repository settings. `master` can remain a development branch. Alternatively,
   keep `master` as default and bring just the reviewed workflow onto it; the
   workflow always checks out the shipping branch and uses its helpers. Do not
   merge development master into `justin-stable` to install automation.
3. Enable Actions in Justin's fork and allow this workflow's `GITHUB_TOKEN`
   `contents:write` for the fork's tags/releases and shipping branch. Set the
   repository Actions variable `JUSTIN_DMS_ENABLED` to `true`. No PAT, GitHub App
   or cross-repository secret is needed. Branch protection that blocks bot pushes
   causes a failure and must be reconciled with direct shipping-branch updates.
   Do not dispatch the upstream-style release/port workflows or provision their
   GitHub App/satellite repository secrets.
4. Dispatch **Justin stable bundle** on `justin-stable`, initially with
   `sync=false`. Inspect the checks, metadata, checksums and published assets.
   Subsequent daily checks read published upstream stable releases, preserve
   Justin's patches and publish only after checks pass. They never push upstream
   or create PRs, issues or comments anywhere.
5. Follow `DMS-FORK.md` in `justin-bazzite-dx` after the first real bundle exists.
   Reconcile that checkout with its newer `origin/main`, populate the image lock,
   and review and publish the image changes before building the image. The lock
   remains unconfigured until a real successful bundle has been published.

Upstream `.github/` updates are deliberately excluded from sync merges; review
CI changes separately on the fork. Changes to other workflow files in shipping
commits may require manual publication with appropriately authorized workflow
permissions; this pipeline does not store a broader credential to bypass that
restriction.

The image independently polls only successful **published fork bundles** on its
daily build and dispatch, commits the exact release/hash in its own repository,
and builds that exact commit in the same run. This accounts for
[GitHub's token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow):
bot pushes/releases do not start ordinary downstream push/release workflows.

All additions run in CI or during image construction. No client updater, timer,
background process, extra idle CPU, or retained runtime memory is introduced.
