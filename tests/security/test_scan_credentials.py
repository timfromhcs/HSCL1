"""Credential scan for prebuilt images."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import scan_credentials as sc  # noqa: E402


def make_root(tmp, users=(), shadow=(), host_keys=(), machine_id=None, ssh_home=None):
    (tmp / "etc/ssh").mkdir(parents=True)
    passwd = ["root:x:0:0:root:/root:/bin/bash", "daemon:x:1:1::/usr/sbin:/usr/sbin/nologin"]
    for name, uid in users:
        passwd.append(f"{name}:x:{uid}:{uid}::/home/{name}:/bin/bash")
        (tmp / "home" / name).mkdir(parents=True)
    (tmp / "etc/passwd").write_text("\n".join(passwd) + "\n")
    (tmp / "etc/shadow").write_text("\n".join(f"{n}:{h}:19000:0:99999:7:::" for n, h in shadow) + "\n")
    for k in host_keys:
        (tmp / "etc/ssh" / k).write_text("key")
    if machine_id is not None:
        (tmp / "etc/machine-id").write_text(machine_id)
    if ssh_home:
        (tmp / "home" / ssh_home / ".ssh").mkdir()
    return tmp


def test_clean_oem_image_passes(tmp_path):
    root = make_root(tmp_path, users=[("oem", 1000)], shadow=[("oem", "!"), ("root", "*")], machine_id="")
    assert sc.scan(root, {"oem"}, []) == []


def test_extra_login_account_and_hash_are_found(tmp_path):
    root = make_root(tmp_path, users=[("oem", 1000), ("tester", 1001)], shadow=[("oem", "!"), ("tester", "$y$j9T$abc")])
    f = sc.scan(root, {"oem"}, [])
    assert any("login account present: tester" in x for x in f)
    assert any("password hash: tester" in x for x in f)
    assert any("home directory of a non-allowed user: tester" in x for x in f)


def test_usable_hash_on_allowed_oem_account_is_not_flagged_by_itself(tmp_path):
    # the OEM account is created by the installer and removed at first boot; allowing it is explicit
    root = make_root(tmp_path, users=[("oem", 1000)], shadow=[("oem", "$y$j9T$abc")])
    assert sc.scan(root, {"oem"}, []) == []


def test_ssh_keys_machine_id_are_found(tmp_path):
    root = make_root(tmp_path, users=[("oem", 1000)], shadow=[], host_keys=["ssh_host_ed25519_key"], machine_id="abcdef\n", ssh_home="oem")
    f = "\n".join(sc.scan(root, {"oem"}, []))
    assert "ssh host key present" in f and "machine-id is set" in f and "ssh directory in home: oem" in f


def test_secret_strings_are_found_without_printing_them(tmp_path):
    root = make_root(tmp_path, users=[("oem", 1000)])
    (root / "var/log").mkdir(parents=True)
    (root / "var/log/installer.log").write_text("password=SuperSecret123")
    f = sc.scan(root, {"oem"}, ["SuperSecret123"])
    assert f == ["secret string found in /var/log/installer.log"]
    assert all("SuperSecret123" not in x for x in f)


def test_not_a_root_fs_is_rejected(tmp_path, capsys):
    sys.argv = ["scan", str(tmp_path)]
    assert sc.main() == 2
