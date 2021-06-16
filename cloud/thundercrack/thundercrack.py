#!/usr/bin/env python3

import argparse
import binascii
import collections
import json
import os
import requests
import shlex
import sys
import tempfile

from libcloud.compute import base
from libcloud.compute import deployment
from libcloud.compute import types
from libcloud.compute import providers
from libcloud.compute import ssh
from paramiko import pkey
from paramiko import ecdsakey

from typing import (
        NamedTuple, Sequence, Optional, List, Tuple, Dict, Any, NoReturn)


HASHCAT_RELEASES_URL = \
    "https://api.github.com/repos/hashcat/hashcat/releases/latest"
HASHCAT_BIN_PATH = "/root/hashcat/hashcat.bin"
PASSWD_FILE_PATH = "/root/passwd"
WORDLIST_FILE_PATH = "/root/wordlist"

STATUS_OK = 'ok'
STATUS_ERROR = 'error'

msg_prefix = {
        STATUS_OK: '[+] ',
        STATUS_ERROR: '[!] ',
}


def print_msg(msg: str, status: str = STATUS_OK) -> None:
    print('{}{}'.format(msg_prefix[status], msg), flush=True)


def get_driver(
        account_name: Optional[str] = None,
        json_path: str = "",
        project_id: Optional[str] = None,
        zone: Optional[str] = None) -> base.NodeDriver:
    """Build a driver instance."""
    if not (account_name and project_id):
        metadata = parse_sa(json_path)
        account_name = account_name or metadata.account_name
        project_id = project_id or metadata.project_id
    compute_engine = providers.get_driver(types.Provider.GCE)
    return compute_engine(
            account_name, json_path, project=project_id,
            datacenter=zone)


class Metadata(NamedTuple):
    project_id: str
    account_name: str


def parse_sa(json_path: str) -> Metadata:
    """Extract the project ID and account name from the JSON credentials."""
    with open(json_path) as fp:
        data = json.load(fp)
    return Metadata(
            project_id=data['project_id'],
            account_name=data['client_email'])


class ThunderCrackArgs(argparse.Namespace):
    """Type for command-line args."""
    service_account: str
    credentials: str
    project: str
    zone: str
    size: str
    gpu: str
    gpus: int
    ssh_key: Optional[str]
    disk_size: int
    wordlist: Optional[str]
    hashfile: Optional[str]
    benchmark: bool
    debug_cmd: bool
    hashcat_args: List[str]


def get_args(argv: Sequence[str]) -> ThunderCrackArgs:
    parser = argparse.ArgumentParser(
            description='Hashcat on Cloud',
            allow_abbrev=False)
    parser.add_argument(
            '--service_account', default='', help='Service Account Name')
    parser.add_argument(
            '--credentials', default='', help='Path to SA Credentials',
            required=True)
    parser.add_argument(
            '--project', default='', help='Project ID')
    parser.add_argument(
            '--zone', default='us-central1-a',
            help='Zone for Compute Instance')
    parser.add_argument(
            '--size', default='n1-standard-2', help='Instance Size')
    parser.add_argument(
            '--gpu', default='nvidia-tesla-v100', help='GPU Type')
    parser.add_argument(
            '--gpus', default=1, type=int, help='Number of GPUs',
            metavar='N_GPUS')
    parser.add_argument(
            '--ssh_key', default=None, help='SSH Key Path')
    parser.add_argument(
            '--disk_size', default=10, type=int, help='Disk size in GB')
    parser.add_argument(
            '--wordlist', default=None, help='Wordlist for wordlist modes.')
    parser.add_argument(
            '--hashfile', default=None, help='File for hashes.')
    parser.add_argument(
            '--benchmark', default=False, action='store_true',
            help='Run benchmarks instead of cracking.')
    parser.add_argument(
            '--debug_cmd', default=False, action='store_true',
            help='Debugging command: print hashcat command line only.')
    parser.add_argument(
            'hashcat_args', nargs='*', default=[],
            help='Extra arguments for hashcat.')
    args, extras = parser.parse_known_args(
            argv[1:],
            namespace=ThunderCrackArgs())
    assert isinstance(args, ThunderCrackArgs)  # Help typer with return value
    args.hashcat_args = extras + args.hashcat_args
    if not (args.benchmark or args.hashfile):
        print('Must specify --hashfile or --benchmark!\n', file=sys.stderr)
        parser.print_usage()
        parser.exit(2)
    return args


def list_available_choices(driver: base.NodeDriver) -> None:
    for image in driver.list_images():
        print(image)
    for size in driver.list_sizes():
        print(size)


def get_image(
        driver: base.NodeDriver, basename: str = 'debian-10') -> base.NodeImage:
    """Find an image that starts with a given name."""
    for image in driver.list_images():
        if image.name.startswith(basename):
            return image
    raise ValueError('No image found with basename {}'.format(basename))


def get_size(
        driver: base.NodeDriver, name: str = 'n1-standard-2') -> base.NodeSize:
    for size in driver.list_sizes():
        if size.name == name:
            return size
    raise ValueError('No size found with name {}'.format(name))


def get_ssh_key(key_path: Optional[str] = None) -> pkey.PKey:
    if key_path:
        return pkey.PKey.from_private_key_file(key_path)
    return ecdsakey.ECDSAKey.generate()


def get_instance_name() -> str:
    uid = binascii.hexlify(os.urandom(6)).decode('ascii')
    return 'thundercrack-{}'.format(uid)


class ScriptFailedError(Exception):
    """Error when script failed."""


class CheckedMultiStepDeployment(deployment.MultiStepDeployment):

    def run(self, node: base.Node, client: ssh.BaseSSHClient) -> base.Node:
        """
        Run each deployment that has been added.

        ScriptDeployment returns are checked.
        """
        for s in self.steps:
            print_msg('Running step: {!r}'.format(s))
            node = s.run(node, client)
            if isinstance(s, deployment.ScriptDeployment):
                if s.exit_status != 0:
                    print_msg('Step failed: {}'.format(s.stderr), STATUS_ERROR)
                    raise ScriptFailedError('Failed Script: {!r}'.format(s))
        return node


def split_hashargs(args: List[str]) -> Tuple[List[str], List[str]]:
    """Split any patterns off the end of the hashcat args."""
    patterns = []
    args = args[:]  # Making a copy
    while args:
        if args[-1].startswith('?'):
            patterns.append(args.pop())
        else:
            break
    return args, patterns[::-1]


def build_hashcat_command(args: ThunderCrackArgs) -> str:
    """Build the hashcat command line."""
    if args.benchmark:
        cmd = [
                HASHCAT_BIN_PATH,
                "-b",
        ]
        cmd.extend(args.hashcat_args)
    else:
        cmd = [
                HASHCAT_BIN_PATH,
                "-o",
                PASSWD_FILE_PATH + ".out",
        ]
        hashcat_args, patterns = split_hashargs(args.hashcat_args)
        cmd.extend(hashcat_args)
        cmd.append(PASSWD_FILE_PATH)
        if args.wordlist:
            cmd.append(WORDLIST_FILE_PATH)
        cmd.extend(patterns)
    return shlex.join(cmd)


def build_tmux_command(args: ThunderCrackArgs) -> str:
    """Build the tmux line."""
    hashcat_cmd = build_hashcat_command(args)
    print_msg('Hashcat command line: {}'.format(hashcat_cmd))
    cmd = [
            "tmux",
            "new-session",
            "-d",
            hashcat_cmd + ";/bin/bash -i",
    ]
    return shlex.join(cmd)


def get_deploy_steps(args: ThunderCrackArgs) -> CheckedMultiStepDeployment:
    """Get the deployment steps."""
    hashcat_url = get_hashcat_download()
    setup_script_steps = [
            "cd /root",
            "sed -i 's/ main/ main contrib non-free/' /etc/apt/sources.list",
            "apt-get update",
            "DEBIAN_FRONTEND=noninteractive apt-get -y install p7zip wget tmux "
                "linux-headers-$(uname -r)",
            "DEBIAN_FRONTEND=noninteractive apt-get -t buster-backports -y "
                "install nvidia-cuda-dev "
                "nvidia-cuda-toolkit nvidia-driver",
            "modprobe nvidia",
            "wget -O /tmp/hashcat.7z {}".format(hashcat_url),
            "7zr x /tmp/hashcat.7z",
            "ln -s hashcat-* hashcat",
    ]
    setup_script = ' && '.join(setup_script_steps)
    setup_deployment = deployment.ScriptDeployment(setup_script)

    steps = CheckedMultiStepDeployment([setup_deployment])

    if not args.benchmark:
        ensure_file_exists(
                args.hashfile, "Hash file {} missing!".format(args.hashfile))
        hash_deployment = deployment.FileDeployment(
                str(args.hashfile), PASSWD_FILE_PATH)

        steps.add(hash_deployment)

        if args.wordlist is not None:
            ensure_file_exists(
                    str(args.wordlist),
                    "Wordlist {} missing!".format(args.wordlist))
            wordlist_deployment = deployment.FileDeployment(
                    args.wordlist, WORDLIST_FILE_PATH)
            steps.add(wordlist_deployment)

    tmux_cmd = build_tmux_command(args)
    tmux_deployment = deployment.ScriptDeployment(tmux_cmd)
    steps.add(tmux_deployment)

    return steps


def get_hashcat_download() -> Optional[str]:
    """Get the URL for the hashcat download."""
    resp = requests.get(HASHCAT_RELEASES_URL)
    body = resp.json()
    for asset in body['assets']:
        url = asset['browser_download_url']
        if url.endswith('.7z'):
            return url
    return None


def build_vm(
        driver: base.NodeDriver,
        image: base.NodeImage,
        size: base.NodeSize,
        gpu_type: str,
        gpus: int,
        ssh_key: pkey.PKey,
        disk_size: int,
        deploy_steps: deployment.Deployment) -> base.Node:
    """Build the VM."""
    kwargs: Dict[str, Any] = dict()
    if gpus:
        kwargs['ex_accelerator_type'] = gpu_type
        kwargs['ex_accelerator_count'] = gpus
        kwargs['ex_on_host_maintenance'] = 'TERMINATE'
    name = get_instance_name()
    print_msg('New instance will be named: {}'.format(name))
    pubkey = '{} {}'.format(ssh_key.get_name(), ssh_key.get_base64())
    metadata = {
        'items': [
            {
                'key': 'ssh-keys',
                'value': 'root: {}'.format(pubkey)
            }
        ]
    }
    driver._build_service_accounts_gce_list = (  # type: ignore
            lambda *args, **kwargs: [])

    # Write temporary path
    with tempfile.NamedTemporaryFile('w') as tmpf:
        ssh_key.write_private_key(tmpf)
        tmpf.flush()
        print_msg("Starting build/deploy steps.")
        print_msg("Note: this can take several minutes for the instance to "
                "become ready, hashcat to be deployed, etc.")
        node = driver.deploy_node(
                name=name,
                image=image,
                size=size,
                ex_metadata=metadata,
                deploy=deploy_steps,
                ssh_key=tmpf.name,
                ex_disk_size=disk_size,
                ex_service_accounts=[],
                **kwargs)
        return node


def ensure_file_exists(
        path: Optional[str],
        error: str = 'Required file missing.') -> Optional[NoReturn]:
    if path is None:
        print_msg(error, STATUS_ERROR)
        sys.exit(1)
    try:
        if not os.path.isfile(path):
            print_msg(error, STATUS_ERROR)
            sys.exit(1)
    except TypeError:
        print_msg(error, STATUS_ERROR)
        sys.exit(2)
    return None


def main(argv: List[str]) -> None:
    args = get_args(argv)
    if args.debug_cmd:
        print(build_hashcat_command(args))
        return
    print_msg("Getting driver and setting up...")
    driver = get_driver(
            account_name=args.service_account,
            json_path=args.credentials,
            project_id=args.project,
            zone=args.zone)
    image = get_image(driver)
    size = get_size(driver, name=args.size)
    key = get_ssh_key(args.ssh_key)
    print_msg("Setting up deploy steps...")
    deploy_steps = get_deploy_steps(args)
    print_msg("Starting build...")
    node = build_vm(driver, image, size, args.gpu, args.gpus, key,
             args.disk_size, deploy_steps)
    print_msg(
        "Started hashcat.  SSH to instance attach to TMUX to see status/output")
    print_msg("gcloud compute ssh {}".format(node.name))


if __name__ == '__main__':
    main(sys.argv)
