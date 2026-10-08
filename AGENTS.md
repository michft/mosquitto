# Agent instructions

Use caveman mode unless user requests normal mode. Keep edits narrow.

## JJ workflow

- Colocated JJ/Git. Prefer JJ; inspect `jj --ignore-working-copy status` and log
  before snapshotting. Check secret ignores first. Preserve user changes.
- Separate unrelated tasks. Before handoff: meaningful `jj describe`, concise
  task bookmark, then `jj new`; verify clean working copy.
- Never import `/opt/mosquitto` Git history or credentials. Remote is
  `https://github.com/michft/mosquitto`; publishing requires explicit user
  authorization. Prior remote main is preserved at `pre-local-main-20261008`.

## Broker and credentials

- Track reviewed public Mosquitto config and launcher/service templates here.
  Never track/copy password files or hashes, private `.env.apple`, keys, broker
  persistence DB, logs or raw container inspect containing credentials.
- Live config is in Apple Container volume `mosquitto-config`; this checkout is
  not the mounted runtime. Launcher remains `/opt/mosquitto/bin/mosquitto-container`.
- Do not install, seed volumes, restart/recreate containers, modify accounts/ACLs,
  change listeners, run builds/dev servers unless requested. Read-only inspection
  and preparation are allowed. Ask before changing user-authored work.
- Standing user approval, 2026-10-08: all MQTT broker permission expansions
  for local access are approved for future work, including local accounts, ACLs
  and topic permissions. A requested broker expansion implicitly authorizes its
  required local permission expansion; do not ask for separate confirmation.
  This standing approval satisfies the accounts/ACL authorization rule above.
  Local access scope does not authorize internet exposure. Keep credentials private.
- Preserve existing Frigate/HA users, topics, authentication, persistence and
  network restrictions. A sample uploader ACL is not a complete replacement ACL.
- Frigate config belongs in `../frigate`; uploader code/AWS/HA source in
  `../homeassistant`. Follow `../homeassistant/MQTT-UPLOADER-PLAN.md`.
- Validate copied launcher with `zsh -n bin/mosquitto-container`, plist with
  `plutil -lint launchd/local.mosquitto.apple-container.plist`; verify ignores
  before JJ snapshots. Broker config changes need matching-version validation
  in an explicitly requested isolated test or deployment; no automatic server run.
- Update docs when broker behavior/setup changes.
