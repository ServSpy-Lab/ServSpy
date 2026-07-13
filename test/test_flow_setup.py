import argparse
import json
import os
import re
import sys
from unittest.mock import MagicMock

import pytest

package_dictionary = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dictionary not in sys.path:
    sys.path.insert(0, package_dictionary)

import src.flow_setup as fs

TEST_PORT = 9000


@pytest.fixture
def mocked_popen(monkeypatch):
    """Mock subprocess.Popen (default Windows); auto-cleanup temp files."""
    popen = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(fs.subprocess, 'Popen', popen)
    monkeypatch.setattr(fs.platform, 'system', lambda: 'Windows')
    yield popen
    if popen.call_args is None:
        return
    cmd = popen.call_args.args[0]
    if isinstance(cmd, (list, tuple)):
        try:
            path = cmd[cmd.index('--config-file') + 1]
        except (ValueError, IndexError):
            return
    else:
        m = re.search(r'--config-file\s+"([^"]+)"', cmd)
        if not m:
            m = re.search(r'--config-file\s+(\S+)', cmd)
        path = m.group(1) if m else None
    if path and os.path.exists(path):
        os.unlink(path)


@pytest.mark.parametrize(
    'addr,expected',
    [
        (' 127.0.0.1:8080 ', ('127.0.0.1', 8080)),
        ('10.0.0.1:443', ('10.0.0.1', 443)),
    ],
)
def test_parse_addr_port(addr, expected):
    assert fs.parse_addr_port(addr) == expected


def test_parse_addr_port_invalid():
    with pytest.raises(ValueError):
        fs.parse_addr_port('not-a-port')


@pytest.mark.parametrize(
    'complete_fn,defaults,key',
    [
        (fs.complete_server_config, fs.SERVER_DEFAULTS, 'max_clients'),
        (fs.complete_client_config, fs.CLIENT_DEFAULTS, 'max_custom_workers'),
    ],
)
def test_complete_config_overrides_and_fills(complete_fn, defaults, key):
    cfg = complete_fn({'host': '0.0.0.0', 'port': TEST_PORT})
    assert cfg['host'] == '0.0.0.0'
    assert cfg['port'] == TEST_PORT
    assert cfg[key] == defaults[key]


@pytest.mark.parametrize(
    'complete_fn,defaults_dict',
    [
        (fs.complete_server_config, fs.SERVER_DEFAULTS),
        (fs.complete_client_config, fs.CLIENT_DEFAULTS),
    ],
)
def test_complete_config_does_not_mutate_defaults(complete_fn, defaults_dict):
    before = dict(defaults_dict)
    complete_fn({'port': 9999})
    assert defaults_dict == before


def test_generate_configs_server():
    args = argparse.Namespace(type=0, setup_addr_port='127.0.0.1:8080', connect_addr_port=None, setup_num=1)
    servers, clients = fs.generate_configs_from_args(args)
    assert servers == [{'host': '127.0.0.1', 'port': 8080}]
    assert clients == []


def test_generate_configs_client():
    args = argparse.Namespace(type=1, setup_addr_port='127.0.0.1:8080', connect_addr_port='10.0.0.1:9090', setup_num=1)
    servers, clients = fs.generate_configs_from_args(args)
    assert servers == []
    assert clients == [{'client_host': '127.0.0.1', 'client_port': 8080, 'host': '10.0.0.1', 'port': 9090}]


def test_generate_configs_ignores_setup_num(capsys):
    args = argparse.Namespace(type=0, setup_addr_port='127.0.0.1:8080', connect_addr_port=None, setup_num=3)
    servers, _ = fs.generate_configs_from_args(args)
    assert servers == [{'host': '127.0.0.1', 'port': 8080}]
    assert 'ignored' in capsys.readouterr().out


def test_save_config_writes_completed_single(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fs.save_config([{'host': '0.0.0.0', 'port': TEST_PORT}], [])
    data = json.loads((tmp_path / 'setup.json').read_text(encoding='utf-8'))
    assert len(data['servers']) == 1
    assert data['servers'][0]['host'] == '0.0.0.0'
    assert data['servers'][0]['port'] == TEST_PORT
    assert 'max_clients' in data['servers'][0]


def test_save_config_keeps_only_last_of_each(monkeypatch, tmp_path):
    # Current behavior: only the last server and last client are persisted.
    monkeypatch.chdir(tmp_path)
    servers = [{'host': 'a', 'port': 1}, {'host': 'b', 'port': 2}]
    clients = [{'host': 'c', 'port': 3}, {'host': 'd', 'port': 4}]
    fs.save_config(servers, clients)
    data = json.loads((tmp_path / 'setup.json').read_text(encoding='utf-8'))
    assert [s['host'] for s in data['servers']] == ['b']
    assert [c['host'] for c in data['clients']] == ['d']


def test_save_config_empty_lists(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fs.save_config([], [])
    data = json.loads((tmp_path / 'setup.json').read_text(encoding='utf-8'))
    assert data == {'servers': [], 'clients': []}


def test_load_existing_config_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert fs.load_existing_config() == {'servers': [], 'clients': []}


def test_load_existing_config_present(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'setup.json').write_text(json.dumps({'servers': [{'host': 'x', 'port': 1}], 'clients': []}), encoding='utf-8')
    data = fs.load_existing_config()
    assert data['servers'][0]['host'] == 'x'


@pytest.mark.parametrize(
    'system,which_return,instance_type,expected_arg',
    [
        ('Windows', None, 'server', '--launch_server'),
        ('Linux', 'xterm', 'client', '--launch_client'),
        ('Darwin', None, 'server', '--launch_server'),
        ('Linux', None, 'server', '--launch_server'),
        ('FreeBSD', None, 'client', '--launch_client'),
    ],
)
def test_launch_instance_os_branches(  # noqa: PLR0913
    monkeypatch, mocked_popen, system, which_return, instance_type, expected_arg
):
    monkeypatch.setattr(fs.platform, 'system', lambda: system)
    if which_return is not None:
        monkeypatch.setattr(fs.shutil, 'which', lambda t: which_return)
    elif system == 'Linux':
        monkeypatch.setattr(fs.shutil, 'which', lambda t: None)

    fs.launch_instance({'host': '127.0.0.1', 'port': 65000}, instance_type)
    mocked_popen.assert_called_once()
    cmd = mocked_popen.call_args.args[0]
    if system in ('Windows', 'Darwin') or (system == 'Linux' and which_return):
        assert isinstance(cmd, str)
    else:
        assert isinstance(cmd, list)
    cmd_repr = cmd if isinstance(cmd, str) else ' '.join(cmd)
    assert expected_arg in cmd_repr
    assert '--config-file' in cmd_repr


def test_launch_instance_popen_failure(monkeypatch, capsys):
    """Exception in Popen is caught, error printed, temp file cleaned up."""

    def failing_popen(*args, **kwargs):
        raise OSError('mock failure')

    monkeypatch.setattr(fs.subprocess, 'Popen', failing_popen)
    monkeypatch.setattr(fs.platform, 'system', lambda: 'Windows')

    fs.launch_instance({'host': '127.0.0.1', 'port': 65000}, 'server')

    captured = capsys.readouterr()
    assert 'Failed to launch instance' in captured.out
    assert 'mock failure' in captured.out


def test_run_launched_instance_server_constructs(monkeypatch, tmp_path):
    server_mock = MagicMock()
    monkeypatch.setattr(fs, 'TCP_Server_Base', server_mock)
    cfg = {'host': '127.0.0.1', 'port': 65000}
    path = tmp_path / 'cfg.json'
    path.write_text(json.dumps(cfg), encoding='utf-8')
    fs.run_launched_instance('server', str(path))
    server_mock.assert_called_once_with(**cfg)
    assert not path.exists()


def test_run_launched_instance_client_constructs(monkeypatch, tmp_path):
    client_mock = MagicMock()
    monkeypatch.setattr(fs, 'TCP_Client_Base', client_mock)
    cfg = {'host': '127.0.0.1', 'port': 65000}
    path = tmp_path / 'cfg.json'
    path.write_text(json.dumps(cfg), encoding='utf-8')
    fs.run_launched_instance('client', str(path))
    client_mock.assert_called_once_with(**cfg)


def test_run_launched_instance_unlink_cleanup_fails(monkeypatch, tmp_path):
    """Inner except: pass catches os.unlink failure."""
    server_mock = MagicMock()
    monkeypatch.setattr(fs, 'TCP_Server_Base', server_mock)
    monkeypatch.setattr(fs.os, 'unlink', MagicMock(side_effect=PermissionError('denied')))
    cfg = {'host': '127.0.0.1', 'port': 65000}
    path = tmp_path / 'cfg.json'
    path.write_text(json.dumps(cfg), encoding='utf-8')
    fs.run_launched_instance('server', str(path))
    server_mock.assert_called_once_with(**cfg)


def test_run_launched_instance_missing_file_exits(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda *a, **k: '')
    with pytest.raises(SystemExit):
        fs.run_launched_instance('server', '/no/such/file.json')


@pytest.mark.parametrize(
    'inputs_seq,expected_servers,expected_clients',
    [
        (['0', '127.0.0.1:8080', 'n'], [{'host': '127.0.0.1', 'port': 8080}], []),
        (['1', '127.0.0.1:8080', '10.0.0.1:9090', 'n'], [], [{'client_host': '127.0.0.1', 'client_port': 8080, 'host': '10.0.0.1', 'port': 9090}]),
        # Retry paths: invalid type, invalid bind addr
        (['2', '0', 'bad', '127.0.0.1:8080', 'n'], [{'host': '127.0.0.1', 'port': 8080}], []),
        # Retry paths: invalid type, invalid bind addr, invalid connect addr
        (
            ['x', '1', 'bad', '127.0.0.1:8080', 'bad2', '10.0.0.1:9090', 'n'],
            [],
            [{'client_host': '127.0.0.1', 'client_port': 8080, 'host': '10.0.0.1', 'port': 9090}],
        ),
    ],
)
def test_interactive_collect(monkeypatch, inputs_seq, expected_servers, expected_clients):
    inputs = iter(inputs_seq)
    monkeypatch.setattr('builtins.input', lambda *a, **k: next(inputs))
    servers, clients = fs.interactive_collect()
    assert servers == expected_servers
    assert clients == expected_clients
