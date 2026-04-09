#!/usr/bin/env python3

import argparse
import binascii
import json
import logging
import os
import pathlib
import requests
import shlex
import sys
import tempfile
import time

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

# Configure logging
logger = logging.getLogger('thundercrack')

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


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
    verbose: bool
    instance_name: Optional[str]
    spot: bool
    auto_shutdown: bool
    download_results: bool
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
            '--verbose', default=False, action='store_true',
            help='Enable verbose logging.')
    parser.add_argument(
            '--instance_name', default=None, help='Custom instance name.')
    parser.add_argument(
            '--spot', default=False, action='store_true',
            help='Use spot (preemptible) instances to save cost.')
    parser.add_argument(
            '--auto_shutdown', default=False, action='store_true',
            help='Automatically shut down the instance after hashcat finishes.')
    parser.add_argument(
            '--download_results', default=False, action='store_true',
            help='Wait for hashcat to finish and download the results.')
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
        driver: base.NodeDriver,
        basename: str = 'debian-13') -> base.NodeImage:
    """Find an image that starts with a given name."""
    for image in driver.list_images():
        if image.name.startswith(basename):
            return image
    raise ValueError('No image found with basename {}'.format(basename))


def get_size(
        driver: base.NodeDriver,
        name: str = 'n1-standard-2') -> base.NodeSize:
    for size in driver.list_sizes():
        if size.name == name:
            return size
    raise ValueError('No size found with name {}'.format(name))


def get_ssh_key(key_path: Optional[str] = None) -> pkey.PKey:
    if key_path:
        return pkey.PKey.from_private_key_file(key_path)
    
    # Check for default generated key.
    default_key = pathlib.Path("thundercrack_id_ecdsa")
    if default_key.exists():
        return pkey.PKey.from_private_key_file(str(default_key))
        
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
            logger.info('Running step: %r', s)
            node = s.run(node, client)
            if isinstance(s, deployment.ScriptDeployment):
                if s.exit_status != 0:
                    logger.error('Step failed: %s', s.stderr)
                    raise ScriptFailedError('Failed Script: {!r}'.format(s))
        return node


def split_hashargs(args: List[str]) -> Tuple[List[str], List[str]]:
    """Split any patterns off the end of the hashcat args."""
    if not args:
        return [], []
    for i, arg in enumerate(reversed(args)):
        if not arg.startswith('?'):
            return args[:len(args)-i], args[len(args)-i:]
    # In this case, all args begin with "?"
    return [], args


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
    logger.info('Hashcat command line: %s', hashcat_cmd)
    
    # Touch a marker file when done.
    hashcat_cmd = f"{hashcat_cmd}; touch /tmp/thundercrack_done"

    # If auto_shutdown is requested AND we aren't downloading, append a poweroff command.
    # Note: this will only execute if hashcat finishes (even if it fails).
    if args.auto_shutdown and not args.download_results:
        hashcat_cmd = f"{hashcat_cmd}; logger -t thundercrack 'Auto-shutdown triggered'; poweroff"

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
    if not hashcat_url:
        logger.error("Could not find hashcat download URL")
        sys.exit(1)

    steps = CheckedMultiStepDeployment([])

    # 1. Base dependencies and system prep
    prep_script = [
        "cd /root",
        "sed -i 's/ main/ main contrib non-free/' /etc/apt/sources.list",
        "apt-get update",
        "DEBIAN_FRONTEND=noninteractive apt-get -y install p7zip wget tmux linux-headers-$(uname -r)",
    ]
    steps.add(deployment.ScriptDeployment(' && '.join(prep_script), name='system_prep'))

    # 2. NVIDIA Driver installation
    driver_script = [
        "DEBIAN_FRONTEND=noninteractive apt-get -y install nvidia-cuda-dev nvidia-cuda-toolkit nvidia-driver",
        "modprobe nvidia || true",
    ]
    steps.add(deployment.ScriptDeployment(' && '.join(driver_script), name='driver_install'))

    # 3. Hashcat download and extraction
    hashcat_script = [
        f"wget -O /tmp/hashcat.7z {hashcat_url}",
        "7zr x /tmp/hashcat.7z",
        "rm -f hashcat && ln -s hashcat-* hashcat",
    ]
    steps.add(deployment.ScriptDeployment(' && '.join(hashcat_script), name='hashcat_setup'))

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
    tmux_deployment = deployment.ScriptDeployment(tmux_cmd, name='start_cracking')
    steps.add(tmux_deployment)

    return steps


def get_hashcat_download() -> Optional[str]:
    """Get the URL for the hashcat download."""
    try:
        resp = requests.get(HASHCAT_RELEASES_URL)
        resp.raise_for_status()
        body = resp.json()
        for asset in body.get('assets', []):
            url = asset.get('browser_download_url')
            if url and url.endswith('.7z'):
                return url
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch hashcat releases: %s", e)
    return None


def build_vm(
        driver: base.NodeDriver,
        image: base.NodeImage,
        size: base.NodeSize,
        gpu_type: str,
        gpus: int,
        ssh_key: pkey.PKey,
        ssh_key_path: str,
        disk_size: int,
        deploy_steps: deployment.Deployment,
        instance_name: Optional[str] = None,
        spot: bool = False) -> base.Node:
    """Build the VM."""
    kwargs: Dict[str, Any] = dict()
    if gpus:
        kwargs['ex_accelerator_type'] = gpu_type
        kwargs['ex_accelerator_count'] = gpus
        kwargs['ex_on_host_maintenance'] = 'TERMINATE'
    
    if spot:
        kwargs['ex_preemptible'] = True
    
    name = instance_name or get_instance_name()
    logger.info('New instance will be named: %s', name)
    pubkey = '{} {}'.format(ssh_key.get_name(), ssh_key.get_base64())
    metadata = {
        'items': [
            {
                'key': 'ssh-keys',
                'value': 'root: {}'.format(pubkey)
            }
        ]
    }

    logger.info("Starting build/deploy steps.")
    logger.info(
            "Note: this can take several minutes for the instance to "
            "become ready, hashcat to be deployed, etc.")
    node = driver.deploy_node(
            name=name,
            image=image,
            size=size,
            ex_metadata=metadata,
            deploy=deploy_steps,
            ssh_key=ssh_key_path,
            ex_disk_size=disk_size,
            ex_service_accounts=[],
            **kwargs)
    return node


def wait_and_download(
        node: base.Node,
        key: pkey.PKey,
        args: ThunderCrackArgs) -> None:
    """Wait for results and download them."""
    ip = node.public_ips[0]
    logger.info("Waiting for results from %s...", ip)
    
    # We use paramiko to check for the completion file.
    import paramiko
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Retry loop to connect (instance might still be booting or script running)
    connected = False
    for i in range(120): # 10 minutes (5 second interval)
        try:
            client.connect(ip, username='root', pkey=key, timeout=10)
            connected = True
            break
        except Exception:
            time.sleep(5)
            
    if not connected:
        logger.error("Failed to connect to %s after 10 minutes", ip)
        return

    # Now poll for the file /tmp/thundercrack_done
    logger.info("Connected. Polling for completion...")
    while True:
        _, stdout, _ = client.exec_command('ls /tmp/thundercrack_done')
        if stdout.channel.recv_exit_status() == 0:
            break
        time.sleep(30)
    
    logger.info("Hashcat finished. Downloading results...")
    sftp = client.open_sftp()
    remote_path = PASSWD_FILE_PATH + ".out"
    local_path = "passwd.out"
    try:
        sftp.get(remote_path, local_path)
        logger.info("Results downloaded to %s", local_path)
    except Exception as e:
        logger.error("Failed to download results: %s", e)
    finally:
        sftp.close()
        client.close()

    if args.auto_shutdown:
        logger.info("Auto-shutdown: destroying instance %s", node.name)
        node.destroy()


def ensure_file_exists(
        path: Optional[str],
        error: str = 'Required file missing.') -> Optional[NoReturn]:
    if path is None:
        logger.error(error)
        sys.exit(1)
    if not pathlib.Path(path).is_file():
        logger.error(error)
        sys.exit(1)
    return None


def main(argv: List[str]) -> None:
    args = get_args(argv)
    setup_logging(args.verbose)
    if args.debug_cmd:
        print(build_hashcat_command(args))
        return
    logger.info("Getting driver and setting up...")
    driver = get_driver(
            account_name=args.service_account,
            json_path=args.credentials,
            project_id=args.project,
            zone=args.zone)
    image = get_image(driver)
    size = get_size(driver, name=args.size)
    key = get_ssh_key(args.ssh_key)
    
    # Save the key if it was generated and doesn't exist.
    if not args.ssh_key:
        key_path = pathlib.Path("thundercrack_id_ecdsa")
        if not key_path.exists():
            key.write_private_key_file(str(key_path))
            key_path.chmod(0o600)
            logger.info("Generated new SSH key and saved to %s", key_path)
        else:
            logger.info("Using existing generated key %s", key_path)

    logger.info("Setting up deploy steps...")
    deploy_steps = get_deploy_steps(args)
    
    # Use a temporary file to pass the key to libcloud's deploy_node.
    with tempfile.NamedTemporaryFile('w', delete=True) as tmpf:
        key.write_private_key(tmpf)
        tmpf.flush()
        
        logger.info("Starting build...")
        node = build_vm(
                driver, image, size, args.gpu, args.gpus, key,
                tmpf.name, args.disk_size, deploy_steps,
                instance_name=args.instance_name, spot=args.spot)
        
    logger.info(
        "Started hashcat. SSH to instance attach to TMUX to see status/output")
    logger.info("gcloud compute ssh %s", node.name)

    if args.download_results:
        if not node.public_ips:
            logger.error("No public IP available for results download.")
        else:
            wait_and_download(node, key, args)


if __name__ == '__main__':
    main(sys.argv)
