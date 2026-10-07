# Handoff: broker support for Frigate video uploads

Prepared 2026-10-08. Start at `/Users/mt/src/mosquitto`.

Read [AGENTS.md](AGENTS.md), [README.md](README.md), and canonical
[MQTT uploader design/plans](../homeassistant/MQTT-UPLOADER-PLAN.md).
Use caveman skill; use handoff skill when handing work onward. No subagents requested.

## Verified baseline

Existing Mosquitto already serves Frigate. Public config copied into this repo
matches inspected live config. Authentication required, broker persistence enabled;
passwords/state/history excluded. Launcher and launchd template are snapshots;
runtime remains `/opt/mosquitto` plus existing named volumes. No deployment done.

Frigate source inspection confirmed person-event notifications and per-attempt
face recognition metadata. Current publisher QoS 0 cannot be upgraded by merely
subscribing at QoS 1. Frigate QoS 1 change must be prepared/reviewed in its repo.
Certificate-based synthetic S3 upload/viewer downloads passed on 2026-10-07;
MQTT upload service implementation is prepared; deployment, real eligible video
and HA playback still pending.

## Next work here

1. Inspect JJ state without snapshotting, verify secret ignores, check public config
   drift. Do not open/copy password file or import `/opt/mosquitto` Git history.
2. Inventory existing topic/user permissions privately. Prepare dedicated uploader
   subscriber identity and read grants for `frigate/events`,
   `frigate/tracked_object_update`, `frigate/available`. Current config has no ACL
   file; preserve existing Frigate/HA access in any complete proposed ACL.
3. Check persistent-session capacity/queue limits against actual traffic and
   outage requirements. Keep publisher and broker recovery limitations explicit.
4. Coordinate subscriber schemas and service with uploader in `../homeassistant`,
   and publisher QoS/recognition training with `../frigate`. Persist attempts and
   completed events; empty identity alone must never authorize an upload.
5. Prepare reviewed deployment changes and private rollback, then arrange any
   required broker/Frigate interruptions. Validate reconnects, duplicate handling,
   recovery and real video viewing per canonical activation plan.

Requested implementation is now prepared: full ACL, bounded persistent queues
and explicit provisioning helper; uploader and Frigate changes are coordinated
in sibling repos. Review/merge the three PRs, run required isolated broker
validation, then follow [operations guide](../homeassistant/MQTT-UPLOADER-OPERATIONS.md)
for deployment. Actual accounts/config and automatic uploading remain unactivated. Repo has no remote; ask user for
publishing destination only if publishing is requested.
