#!/usr/bin/env python3
"""Explicit isolated Mosquitto test; synthetic identities, no production broker writes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import socket
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from paho.mqtt import client as mqtt

CLI = '/opt/homebrew/bin/container'


def command(*args, data=None):
    result = subprocess.run([CLI, *args], input=data, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError('Isolated container command failed: ' + args[0])
    return result.stdout


def wait(predicate, label, seconds=10):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('Timed out: ' + label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-isolated-broker', action='store_true', required=True)
    parser.add_argument('--broker-repo', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18884)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('worker', args.worker)
    worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
    name = 'mqtt-upload-test-' + secrets.token_hex(5)
    passwords = {user: secrets.token_urlsafe(24) for user in ('homeassistant', 'frigate', 'person-s3-uploader')}
    clients = []
    created = False
    with tempfile.TemporaryDirectory(prefix='mqtt-upload-integration-') as folder:
        root = Path(folder); root.chmod(0o755)
        for directory in ('config', 'data', 'log'):
            (root / directory).mkdir(mode=0o777); (root / directory).chmod(0o777)
        # Installed matching-version utility hashes synthetic input only. No
        # production password file is read or modified; output stays in memory.
        source = ''.join(user + ':' + password + '\n' for user, password in passwords.items())
        hashes = command('exec', '--interactive', 'mosquitto', 'sh', '-eu', '-c',
                         'umask 077; p=$(mktemp /tmp/mqtt-fixture.XXXXXX); trap \'rm -f "$p"\' EXIT; cat > "$p"; mosquitto_passwd -U "$p"; cat "$p"', data=source)
        (root / 'config/password.txt').write_text(hashes)
        shutil.copy2(args.broker_repo / 'config/uploader.acl', root / 'config/acl.conf')
        config = (args.broker_repo / 'config/mosquitto.conf').read_text().replace('/mosquitto/', '/test/')
        (root / 'config/mosquitto.conf').write_text(config)
        for file in (root / 'config').iterdir(): file.chmod(0o644)
        try:
            command('run', '--detach', '--name', name, '--publish', f'127.0.0.1:{args.port}:1883',
                    '--cpus', '1', '--memory', '256M', '--mount', f'type=bind,source={root},target=/test',
                    'docker.io/library/eclipse-mosquitto:2.0.22', 'mosquitto', '-c', '/test/config/mosquitto.conf')
            created = True
            def accepting():
                try:
                    with socket.create_connection(('127.0.0.1', args.port), timeout=0.2): return True
                except OSError: return False
            wait(accepting, 'test broker ready', 20)

            def client(user, identity=None, persistent=False, manual=False):
                c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=identity or secrets.token_hex(6),
                                clean_session=not persistent, manual_ack=manual)
                c.username_pw_set(user, passwords[user]); clients.append(c)
                c.connected = threading.Event(); c.messages = []; c.subscribed = threading.Event()
                def connect(c, userdata, flags, reason, properties):
                    if not reason.is_failure: c.connected.set()
                c.on_connect = connect
                c.on_message = lambda c, userdata, msg: c.messages.append(msg)
                c.on_subscribe = lambda *unused: c.subscribed.set()
                c.connect('127.0.0.1', args.port, 10); c.loop_start(); wait(c.connected.is_set, 'client connect')
                return c

            publisher = client('frigate'); ha = client('homeassistant')
            ha.subscribe('#', qos=1); wait(ha.subscribed.is_set, 'HA subscription')
            observer = client('person-s3-uploader', 'test-acl-' + name)
            observer.subscribe([('frigate/events', 1), ('unrelated/topic', 1)])
            wait(observer.subscribed.is_set, 'uploader subscriptions')
            publisher.publish('unrelated/topic', 'existing-user', qos=1).wait_for_publish(5)
            wait(lambda: any(m.payload == b'existing-user' for m in ha.messages), 'existing users retain access')
            time.sleep(0.4)
            assert not observer.messages, 'Uploader received unrelated topic'
            observer.publish('frigate/events', 'forbidden-write', qos=1).wait_for_publish(5)
            time.sleep(0.4)
            assert not any(m.payload == b'forbidden-write' for m in ha.messages), 'Uploader write was allowed'
            ha.subscribed.clear(); ha.subscribe('$SYS/broker/version', qos=1)
            wait(lambda: any(m.topic == '$SYS/broker/version' for m in ha.messages), 'existing HA system-topic access')
            publisher.subscribed.clear(); publisher.subscribe('$SYS/broker/version', qos=1)
            wait(lambda: any(m.topic == '$SYS/broker/version' for m in publisher.messages), 'existing Frigate system-topic access')
            print('PASS ACL: existing user/system-topic access, uploader unrelated-read and write denial', flush=True)

            path = root / 'queue.sqlite3'
            db = worker.open_queue(path, 'test-destination', 0)
            settings = dict(host='127.0.0.1', port=args.port, username='person-s3-uploader',
                            password=passwords['person-s3-uploader'], client_id='test-worker-' + name, topic_prefix='frigate')
            listener = worker.MqttSubscriber(path, settings); listener.start(); wait(listener.ready.is_set, 'worker subscription')
            listener.stop()
            face = json.dumps(dict(type='face', id='100-person', camera='front_door', timestamp=110, name=None, score=0)).encode()
            event = json.dumps(dict(type='end', after=dict(id='100-person', camera='front_door', label='person', start_time=100,
                                 frame_time=120, end_time=120, has_clip=True, false_positive=False, sub_label=None))).encode()
            publisher.publish('frigate/events', event, qos=1).wait_for_publish(5)
            publisher.publish('frigate/tracked_object_update', face, qos=1).wait_for_publish(5)
            command('stop', name); command('start', name)
            listener = worker.MqttSubscriber(path, settings); listener.start(); wait(listener.ready.is_set, 'worker reconnect after broker restart')
            wait(lambda: db.execute('SELECT COUNT(*) FROM face_attempts').fetchone()[0] == 1, 'durable face evidence')
            wait(lambda: db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1, 'durable completion')
            assert worker.unknown_face(json.loads(db.execute('SELECT metadata FROM events').fetchone()[0]))
            listener.stop()
            print('PASS offline QoS 1 queue survives broker restart; face/end ingestion reconnects', flush=True)

            wait(publisher.is_connected, 'publisher reconnect')
            listener = worker.MqttSubscriber(path, settings)
            with patch.object(worker, 'ingest', side_effect=sqlite3.OperationalError('synthetic disk full')):
                listener.start(); wait(listener.ready.is_set, 'failure-test subscriptions')
                publisher.publish('frigate/tracked_object_update', face.replace(b'100-person', b'101-person'), qos=1).wait_for_publish(5)
                wait(listener.failed.is_set, 'uncommitted delivery failure')
                listener.stop()
            assert db.execute("SELECT COUNT(*) FROM face_attempts WHERE id='101-person'").fetchone()[0] == 0
            listener = worker.MqttSubscriber(path, settings); listener.start(); wait(listener.ready.is_set, 'redelivery reconnect')
            wait(lambda: db.execute("SELECT COUNT(*) FROM face_attempts WHERE id='101-person'").fetchone()[0] == 1, 'unacknowledged redelivery')
            publisher.publish('frigate/tracked_object_update', face.replace(b'100-person', b'101-person'), qos=1).wait_for_publish(5)
            time.sleep(0.4)
            assert db.execute("SELECT COUNT(*) FROM face_attempts WHERE id='101-person'").fetchone()[0] == 1
            listener.stop(); db.close()
            print('PASS failed commit leaves delivery unacknowledged; reconnect redelivers; duplicates merge', flush=True)
        finally:
            for c in clients:
                c.disconnect(); c.loop_stop()
            if 'listener' in locals(): listener.stop()
            if created:
                command('stop', name); command('delete', name)
                print('Isolated test container stopped and removed; production broker unchanged', flush=True)


if __name__ == '__main__': main()
