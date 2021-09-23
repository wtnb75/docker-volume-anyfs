import os
import json
import hashlib
import functools
import subprocess
import tempfile
import shutil
import urllib.request
from abc import ABCMeta, abstractmethod
from logging import getLogger
from flask import Flask, Response, Request, request
import click
import yaml
from jinja2 import Template

_log = getLogger(__name__)


class DockerVolumePluginBase(metaclass=ABCMeta):
    app = Flask(__name__)

    def __init__(self):
        methods = ["GET", "POST"]
        methodmap = {
            "/Plugin.Activate": self.Activate,
            "/VolumeDriver.Create": self.Create,
            "/VolumeDriver.Get": self.Get,
            "/VolumeDriver.List": self.List,
            "/VolumeDriver.Remove": self.Remove,
            "/VolumeDriver.Path": self.Path,
            "/VolumeDriver.Mount": self.Mount,
            "/VolumeDriver.Unmount": self.Unmount,
            "/VolumeDriver.Capabilities": self.Capabilities,
        }

        for ep, fn in methodmap.items():
            self.app.add_url_rule(
                ep, fn.__name__,
                view_func=functools.partial(self.do_any, fn, request),
                methods=methods)
        self.app.register_error_handler(500, self.error_500)

    @staticmethod
    def error_500(error):
        content_type = "application/vnd.docker.plugins.v1.1+json"
        return Response(response=json.dumps({"message": str(error)}),
                        status=500, mimetype=content_type)

    def do_any(self, fn, req):
        try:
            data = json.loads(req.data.decode("utf-8"))
            _log.debug("%s %s %s", req.method, req.path, data)
        except Exception:
            _log.debug("%s %s %s", req.method, req.path, req.data)
            data = None
        return fn(req, data)

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)

    def resp_200(self, data={}) -> Response:
        content_type = "application/vnd.docker.plugins.v1.1+json"
        _log.info("response 200 %s", data)
        return Response(response=json.dumps(data), status=200, mimetype=content_type)

    def resp_400(self, data={}) -> Response:
        content_type = "application/vnd.docker.plugins.v1.1+json"
        _log.info("response 400 %s", data)
        return Response(response=json.dumps(data), status=400, mimetype=content_type)

    def Activate(self, req: Request, data: dict):
        res = {
            "Implements": ["VolumeDriver"]
        }
        return self.resp_200(res)

    @abstractmethod
    def Create(self, req: Request, data: dict): pass

    @abstractmethod
    def Mount(self, req: Request, data: dict): pass

    @abstractmethod
    def Path(self, req: Request, data: dict): pass

    @abstractmethod
    def Get(self, req: Request, data: dict): pass

    @abstractmethod
    def List(self, req: Request, data: dict): pass

    @abstractmethod
    def Remove(self, req: Request, data: dict): pass

    @abstractmethod
    def Unmount(self, req: Request, data: dict): pass

    @abstractmethod
    def Capabilities(self, req: Request, data: dict): pass


class AnyVolume(DockerVolumePluginBase):
    mount_info = {
        "davfs2": {
            "mount_command": ["mount.davfs", "-o", "conf=/etc/davfs.conf"],
            "umount_command": ["umount.davfs"],
            "files": {
                "/etc/davfs.conf": "",
            },
        },
        "curlftpfs": {},
        "s3fs": {
            "mount_command": ["s3fs"],
            "strip_options": ["access_key", "secret_key"],
            "umount_command": ["fusermount", "-u"],
            "files": {
                "/root/.passwd-s3fs": {
                    "content": "{{options.access_key}}:{{options.secret_key}}\n",
                    "mode": 0o600,
                }
            }
        },
        "cifs": {},
        "sshfs": {},
        "nfs": {},
        "any": {
            "mount_command": ["mount", "-t", "{{type}}"],
            "umount_command": ["umount"],
        }
    }

    def __init__(self, root, mount_info=None):
        super().__init__()
        self.volroot = os.path.join(root, "volumes")
        self.statefn = os.path.join(root, "state", "fusefs-state.json")
        self.volumes = {}
        if mount_info:
            self.mount_info = mount_info
        self.load()

    def save(self):
        with open(self.statefn, "w") as ofp:
            json.dump(self.volumes, fp=ofp)

    def load(self):
        try:
            with open(self.statefn, "r") as ifp:
                self.volumes = json.load(fp=ifp)
            _log.debug("volumes %s", self.volumes)
        except Exception:
            _log.exception("cannot read state file? %s", self.statefn)

    def Create(self, req, data):
        volname = data.get("Name")
        if not volname:
            return self.resp_400({"message": "no name"})
        opts = {}
        opts["options"] = data.get("Opts", {})
        fstype = opts["options"].pop("type")
        opts["type"] = fstype
        opts["src"] = opts["options"].pop("src")
        if fstype not in self.mount_info:
            return self.resp_400({"message": f"invalid type: {opts.get('type')}"})
        basename = hashlib.sha1(json.dumps(data).encode("utf-8")).hexdigest()
        opts["mountpoint"] = os.path.join(self.volroot, basename)
        if "o" in opts["options"]:
            o = opts["options"].pop("o")
            for kv in o.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    opts["options"][k] = v
                else:
                    opts["options"][kv] = True
        self._do_validate(opts)
        if self.mount_info[fstype].get("download_src", False) and "://" in opts["src"]:
            tfname = tempfile.NamedTemporaryFile("r+", dir=self.volroot, delete=False).name
            _log.info("downloading %s -> %s", opts["src"], tfname)
            res = urllib.request.urlretrieve(opts["src"], tfname)
            _log.info("result: %s", res)
            _log.info("file: %s", os.stat(tfname))
            opts["_url"] = opts["src"]
            opts["src"] = tfname
            opts["_remove"] = tfname
        self.volumes[volname] = opts
        _log.debug("volumes: %s", self.volumes)
        self.save()
        return self.resp_200({})

    def Remove(self, req, data):
        volname = data.get("Name")
        if volname not in self.volumes:
            return self.resp_400({"message": f"no volume: {volname}"})
        vol = self.volumes.pop(volname)
        if "_remove" in vol:
            _log.info("remove tmp file: %s", vol["_remove"])
            try:
                os.unlink(vol["_remove"])
            except Exception:
                _log.exception("cannot unlink %s", vol["_remove"])
        self.save()
        return self.resp_200({})

    def List(self, req, data):
        _log.debug("volumes: %s", self.volumes)
        res = {
            "Volumes": [{"Name": k, "Mountpoint": v.get("mountpoint")} for k, v in self.volumes.items()],
        }
        return self.resp_200(res)

    def Get(self, req, data):
        volname = data.get("Name")
        if volname not in self.volumes:
            return self.resp_400({"message": f"no volume: {volname}"})
        vol = self.volumes.get(volname)
        _log.debug("volume %s %s", volname, vol)
        res = {
            "Volume": {
                "Name": volname,
                "Mountpoint": vol.get("mountpoint"),
            }
        }
        return self.resp_200(res)

    def Path(self, req, data):
        volname = data.get("Name")
        if volname not in self.volumes:
            return self.resp_400({"message": f"no volume: {volname}"})
        vol = self.volumes.get(volname)
        return self.resp_200({"Mountpoint": vol.get("mountpoint")})

    def Mount(self, req, data):
        volname = data.get("Name")
        if volname not in self.volumes:
            return self.resp_400({"message": f"no volume: {volname}"})
        vol = self.volumes.get(volname)
        if "_remove" in vol:
            try:
                _log.info("tmp stat: %s", os.stat(vol["_remove"]))
            except Exception:
                _log.exception("stat failed: %s", vol["_remove"])
        mountpt = vol.get("mountpoint")
        os.makedirs(mountpt, exist_ok=True)
        # mount command
        self._do_mount(mountpt, vol)
        return self.resp_200({"Mountpoint": mountpt})

    def Unmount(self, req, data):
        volname = data.get("Name")
        if volname not in self.volumes:
            return self.resp_400({"message": f"no volume: {volname}"})
        vol = self.volumes.get(volname)
        mountpt = vol.get("mountpoint")
        # umount command
        self._do_unmount(mountpt, vol)
        os.rmdir(mountpt)
        return self.resp_200({})

    def Capabilities(self, req, data):
        res = {
            "Capabilities": {
                "Scope": "local",
            }
        }
        return self.resp_200(res)

    def _render_tmpl(self, s, arg):
        if isinstance(s, str):
            return Template(s).render(arg)
        elif isinstance(s, (list, tuple)):
            return [self._render_tmpl(x, arg) for x in s]
        elif isinstance(s, dict):
            return {k: self._render_tmpl(v, arg) for k, v in s.items()}
        elif isinstance(s, (int, float)):
            return s
        raise Exception(f"invalid template type: {s}")

    def _execute_command(self, cmd, stdin=""):
        if cmd is None:
            return
        # List[str]
        if isinstance(cmd, str):
            _log.debug("execute %s", cmd)
            res = subprocess.run([cmd], input=stdin)
            _log.debug("result: %s", res)
            res.check_returncode()
            return res
        if {isinstance(x, str) for x in cmd} == {True}:
            _log.debug("execute %s", cmd)
            res = subprocess.run(cmd, input=stdin)
            _log.debug("result: %s", res)
            res.check_returncode()
            return res
        if isinstance(cmd, (list, tuple)):
            return [self._execute_command(x) for x in cmd]

    def _do_mount(self, mountpt, vol):
        arg = vol.copy()
        arg["mountpoint"] = mountpt
        tmpl = self.mount_info.get(arg.get("type"))
        volinfo = self._render_tmpl(tmpl, arg)
        _log.debug("arg: %s", arg)
        _log.debug("volinfo: %s", volinfo)
        for fn0, content in volinfo.get("files", {}).items():
            fn1 = self._render_tmpl(fn0, arg)
            _log.info("writing %s", fn1)
            os.makedirs(os.path.dirname(fn1), exist_ok=True, mode=0o700)
            mode = 0o600
            owner = 0
            group = 0
            with open(fn1, "w") as ofp:
                if isinstance(content, dict):
                    content_str = content.get("content", "")
                    mode = content.get("mode", 0o600)
                    owner = content.get("owner", 0)
                    group = content.get("group", 0)
                elif isinstance(content, str):
                    content_str = content
                elif isinstance(content, (list, tuple)):
                    content_str = "\n".join(content)
                print(content_str, file=ofp)
            os.chmod(fn1, mode)
            shutil.chown(fn1, user=owner, group=group)
            _log.debug("stat %s: %s", fn1, os.stat(fn1))
        cmd = volinfo.get("mount_command")
        mount_opts = []
        for k, v in arg.get("options", {}).items():
            if k not in volinfo.get("strip_options", []):
                mount_opts.append("-o")
                if v is True:
                    mount_opts.append(k)
                else:
                    mount_opts.append(f"{k}={v}")
        cmd.extend(mount_opts)
        cmd.append(arg.get("src"))
        cmd.append(arg.get("mountpoint"))
        stdin = arg.get("stdin", "")
        self._execute_command(volinfo.get("pre_mount"))
        self._execute_command(cmd, stdin)
        self._execute_command(volinfo.get("post_mount"))

    def _do_unmount(self, mountpt, vol):
        arg = vol.copy()
        arg["mountpoint"] = mountpt
        tmpl = self.mount_info.get(arg.get("type"))
        volinfo = self._render_tmpl(tmpl, arg)
        cmd = volinfo.get("umount_command", ["umount"])
        cmd.append(mountpt)
        self._execute_command(volinfo.get("pre_umount"))
        self._execute_command(cmd)
        self._execute_command(volinfo.get("post_umount"))
        for fn0 in arg.get("files", {}).keys():
            fn1 = self._render_tmpl(fn0, arg)
            _log.debug("unlink %s", fn1)
            try:
                os.unlink(fn1)
            except Exception:
                _log.exception("unlink failed: %s", fn1)

    def _do_validate(self, vol):
        arg = vol.copy()
        arg["mountpoint"] = "dummy"
        tmpl = self.mount_info.get(arg.get("type"))
        self._render_tmpl(tmpl, arg)
        assert "src" in arg
        for fn0 in arg.get("files", {}).keys():
            self._render_tmpl(fn0, arg)


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default="5000", show_default=True)
@click.option("--root", default="/mnt", show_default=True)
@click.option("--debug/--no-debug", default=False, envvar='DEBUG', show_default=True)
@click.option("--verbose/--no-verbose", default=False, envvar='VERBOSE', show_default=True)
@click.option("--config", type=click.File('r'), default=None)
def main(host, port, debug, verbose, root, config):
    mount_info = None
    if config:
        mount_info = yaml.safe_load(config)
    from logging import basicConfig, DEBUG, INFO
    # logfmt = "%(asctime)-15s %(levelname)s %(threadName)s %(name)s %(message)s"
    logfmt = "%(levelname)s %(threadName)s %(name)s %(message)s"
    if verbose:
        basicConfig(level=DEBUG, format=logfmt)
    else:
        basicConfig(level=INFO, format=logfmt)
    plugin = AnyVolume(root=root, mount_info=mount_info)
    plugin.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
