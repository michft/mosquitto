# Handoff: broker support for Frigate video uploads

Updated 2026-10-08 Australia/Sydney (2026-10-07 UTC). Start at
`/Users/mt/src/mosquitto`.

Read [AGENTS.md](AGENTS.md), [README.md](README.md), and canonical
[MQTT uploader design](../homeassistant/MQTT-UPLOADER-PLAN.md).
Use caveman mode. No subagents requested.

## Current deployment

Broker subscriber/ACL, bounded persistent queues, Frigate LAN endpoint/QoS 1,
upload-enabled Mini worker and HA S3 viewer were deployed under explicit user
authorization. Runtime remains the existing Apple Container services and named
volumes; installed broker launcher remains `/opt/mosquitto`. Credentials and
runtime state remain private, outside tracked files.

`person-s3-uploader` reads only `frigate/events`,
`frigate/tracked_object_update` and `frigate/available`. Existing Frigate/HA
application and system-topic permissions are preserved. Standing approval for
future local permission expansions is recorded in AGENTS.md.

Live retained online delivery at QoS 1 passed after correcting Frigate's broker
host to `192.168.1.106`. Conditional diagnostic S3 PUT, HA viewer exact-byte
signed download and media browsing passed. Final route confirmation was
2026-10-08 07:04 Australia/Sydney (2026-10-07 20:04 UTC).

Isolated Mosquitto 2.0.22 ACL/session/reconnect tests passed; temporary test
container was removed. See [deployment and private rollback record](../homeassistant/MQTT-DEPLOYMENT-2026-10-08.md)
for exact service/config paths and remaining real-event acceptance.

## Remaining work and maintenance

1. Inspect JJ state and verify secret ignores before snapshotting. Preserve
   existing credentials, broker persistence, worker cutoff/queue/receipts and media.
2. Train known faces in Frigate Face Library and observe actual recognition
   attempts. Empty identity alone must never authorize upload. Verify one eligible
   completed unknown-face video uploads and plays in HA; no-face/recognized events
   stay excluded. At deployment there were 78 person events and zero face attempts.
3. Monitor worker status, missed evidence and bounded broker queues. Coordinate
   future publisher changes in `../frigate`, uploader/HA code in `../homeassistant`.
4. Follow [operations](../homeassistant/MQTT-UPLOADER-OPERATIONS.md) for pause,
   private rollback and future deployment. Subscriber is already provisioned;
   provisioning helper refuses password rotation rather than replacing it.

Remote: `https://github.com/michft/mosquitto`. User requested replacement of
remote main with local history; old tip is preserved at `pre-local-main-20261008`.
Review/merge documentation PRs separately from the already deployed runtime.
