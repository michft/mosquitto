# Mosquitto on Mini

Local colocated JJ/Git repo created 2026-10-08 for broker configuration and Apple
Container operation. Public baseline copied from `/opt/mosquitto`; tracked config now prepares
subscriber ACL and bounded offline queues. Live broker remains on original config. No credentials, old Git history or runtime state
copied. No remote configured. This checkout is not deployed.

## Entry points

- [AGENTS.md](AGENTS.md): workflow and runtime boundaries.
- [HANDOFF.md](HANDOFF.md): next agent's MQTT uploader integration work.
- [config/mosquitto.conf](config/mosquitto.conf): current public broker settings.
- [bin/mosquitto-container](bin/mosquitto-container): installed launcher snapshot.
- [launchd definition](launchd/local.mosquitto.apple-container.plist): template still
  invokes `/opt/mosquitto/bin/mosquitto-container`; does not deploy this checkout.
- [.env.example](.env.example): public launcher defaults, not secret credentials.
- [Uploader design/implementation/activation](../homeassistant/MQTT-UPLOADER-PLAN.md).

## Runtime map

- Apple Container service `mosquitto`; launcher default image
  `docker.io/library/eclipse-mosquitto:2.0.22`.
- Config: `/mosquitto/config/mosquitto.conf`, volume `mosquitto-config`.
- Password file: `/mosquitto/config/password.txt`; excluded, never copied here.
- Persistent broker state: `/mosquitto/data/`, volume `mosquitto-data`.
- Logs: `/mosquitto/log/`, volume `mosquitto-log`, plus stdout.
- Private host environment: `/opt/mosquitto/.env.apple`; excluded, not copied.
- launchd: `~/Library/LaunchAgents/local.mosquitto.apple-container.plist`.

Live public config requires authentication, enables persistence, listens internally
on 1883/MQTT and 9001/WebSockets. Launcher defaults publish 1883 on `192.168.1.106`;
9001 is not published by this launcher. Confirm effective environment/container
settings before network changes. Do not broaden access while adding the uploader.

## MQTT uploader work

Frigate currently uses topic prefix `frigate`, QoS 0. Planned host uploader reads
`frigate/events`, `frigate/tracked_object_update`, `frigate/available` directly.
HA remains independent viewer. Worker needs dedicated subscriber identity,
persistent session, commit-before-ack and local durable work queue. Proposed
Frigate publisher QoS 1 belongs in Frigate repo; current broker persistence is
already enabled. MQTT mode/service are implemented in the uploader repo; deployment pending.

Live broker has no ACL directive. Tracked `config/uploader.acl` preserves full
existing `homeassistant`/`frigate` access and grants `person-s3-uploader` read-only
access to its three notification topics. `config/mosquitto.conf` installs that ACL
and bounded persistent queues. Deploy through `bin/provision-uploader --apply`
after review; script refuses unknown users/config drift. Password files
remain private; AWS certificate keys belong to uploader/viewer, not broker config.

## Validation and deployment

Read-only local checks:

```sh
zsh -n bin/mosquitto-container
plutil -lint launchd/local.mosquitto.apple-container.plist
git check-ignore --no-index config/password.txt .env.apple certs/uploader.key
jj --ignore-working-copy status
```

Do not invoke copied launcher's start/restart/recreate/status commands as a check:
its code can start the container system; inspect output may expose runtime values.
Config syntax/runtime validation needs existing matching Mosquitto version in an
explicitly requested isolated test; no server was started during repo creation.

Review live-vs-tracked drift before edits. Plan approved deployment separately:
private backup, install reviewed config into existing named volume, preserve owner
and permissions, arrange controlled broker reload/restart, verify Frigate/HA and
uploader reconnections. Avoid copying older Docker compose or seed scripts into
this Apple Container workflow. Broker outage affects all MQTT clients.

## Subscriber provisioning

`bin/provision-uploader` creates ignored `private/uploader-mqtt.json` (mode 600),
with a generated password, without broker writes. Explicit `--apply` hashes the
password using installed Mosquitto, preserves both existing users, backs up private
files inside the config volume, atomically replaces prepared files and reloads
broker. It refuses existing uploader/rotation, unexpected users, live config drift
and symlink destinations. Do not display the generated JSON or passwords.

```sh
bin/provision-uploader
# After reviewing complete ACL and coordinating deployment:
bin/provision-uploader --apply
```

Then prepare worker with `../homeassistant/bin/configure-person-uploader
--mqtt-config ../mosquitto/private/uploader-mqtt.json`. Follow
[operations guide](../homeassistant/MQTT-UPLOADER-OPERATIONS.md) for observe mode,
activation, pause and rollback. No live broker account/config changed during PR work.
