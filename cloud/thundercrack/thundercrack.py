
import argparse
import binascii
import collections
import json
import os
import requests
import sys
import tempfile

from libcloud.compute import deployment
from libcloud.compute import types
from libcloud.compute import providers
from paramiko import pkey
from paramiko import ecdsakey


HASHCAT_RELEASES_URL = \
    "https://api.github.com/repos/hashcat/hashcat/releases/latest"

STATUS_OK = 'ok'
STATUS_ERROR = 'error'

msg_prefix = {
        STATUS_OK: '[+] ',
        STATUS_ERROR: '[!] ',
}


def print_msg(msg, status=STATUS_OK):
    print('{}{}', msg_prefix[status], msg)


def get_driver(account_name=None, json_path=None, project_id=None, zone=None):
    """Build a driver instance."""
    if not (account_name and project_id):
        metadata = parse_sa(json_path)
        account_name = account_name or metadata.account_name
        project_id = project_id or metadata.project_id
    compute_engine = providers.get_driver(types.Provider.GCE)
    return compute_engine(
            account_name, json_path, project=project_id,
            datacenter=zone)


def parse_sa(json_path):
    """Extract the project ID and account name from the JSON credentials."""
    with open(json_path) as fp:
        data = json.load(fp)
    metadata = collections.namedtuple(
            'metadata', ('project_id', 'account_name'))
    return metadata(
            project_id=data['project_id'],
            account_name=data['client_email'])


def get_args(argv):
    parser = argparse.ArgumentParser(description='Hashcat on Cloud')
    parser.add_argument(
            '--service_account', default='', help='Service Account Name')
    parser.add_argument(
            '--credentials', default='', help='Path to SA Credentials')
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
            '--gpus', default=1, type=int, help='Number of GPUs')
    parser.add_argument(
            '--ssh_key', default=None, help='SSH Key Path')
    parser.add_argument(
            '--disk_size', default=10, type=int, help='Disk size in GB')
    return parser.parse_args(argv[1:])


def list_available_choices(driver):
    for image in driver.list_images():
        print(image)
    for size in driver.list_sizes():
        print(size)


def get_image(driver, basename='debian-10'):
    """Find an image that starts with a given name."""
    for image in driver.list_images():
        if image.name.startswith(basename):
            return image
    raise ValueError('No image found with basename {}'.format(basename))


def get_size(driver, name='n1-standard-2'):
    for size in driver.list_sizes():
        if size.name == name:
            return size
    raise ValueError('No size found with name {}'.format(name))


def get_ssh_key(key_path=None):
    if key_path:
        return pkey.PKey.from_private_key_file(key_path)
    return ecdsakey.ECDSAKey.generate()


def get_instance_name():
    uid = binascii.hexlify(os.urandom(6)).decode('ascii')
    return 'thundercrack-{}'.format(uid)


def get_deploy_steps():
    """Get the deployment steps."""
    hashcat_url = get_hashcat_download()
    setup_script_steps = [
            "cd /root",
            "sed -i 's/ main/ main contrib non-free/' /etc/apt/sources.list",
            "apt-get update",
            "apt-get -y install p7zip wget tmux linux-headers-cloud-amd64",
            "apt-get -t buster-backports -y install nvidia-cuda-dev "
                "nvidia-cuda-toolkit nvidia-driver",
            "modprobe nvidia",
            "wget -O /tmp/hashcat.7z {}".format(hashcat_url),
            "7zr x /tmp/hashcat.7z",
            "ln -s hashcat-* hashcat",
    ]
    setup_script = ' && '.join(setup_script_steps)
    setup_deployment = deployment.ScriptDeployment(setup_script)
    return deployment.MultiStepDeployment([setup_deployment])


def get_hashcat_download():
    """Get the URL for the hashcat download."""
    resp = requests.get(HASHCAT_RELEASES_URL)
    body = resp.json()
    for asset in body['assets']:
        url = asset['browser_download_url']
        if url.endswith('.7z'):
            return url


def build_vm(
        driver, image, size, gpu_type, gpus, ssh_key, disk_size, deploy_steps):
    """Build the VM."""
    kwargs = dict()
    if gpus:
        kwargs['ex_accelerator_type'] = gpu_type
        kwargs['ex_accelerator_count'] = gpus
        kwargs['ex_on_host_maintenance'] = 'TERMINATE'
    name = get_instance_name()
    pubkey = '{} {}'.format(ssh_key.get_name(), ssh_key.get_base64())
    metadata = {
        'items': [
            {
                'key': 'ssh-keys',
                'value': 'root: {}'.format(pubkey)
            }
        ]
    }
    driver._build_service_accounts_gce_list = lambda *args, **kwargs: []

    # Write temporary path
    with tempfile.NamedTemporaryFile('w') as tmpf:
        ssh_key.write_private_key(tmpf)
        tmpf.flush()
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


def main(argv):
    args = get_args(argv)
    driver = get_driver(
            account_name=args.service_account,
            json_path=args.credentials,
            project_id=args.project,
            zone=args.zone)
    image = get_image(driver)
    size = get_size(driver, name=args.size)
    key = get_ssh_key(args.ssh_key)
    deploy_steps = get_deploy_steps()
    build_vm(driver, image, size, args.gpu, args.gpus, key,
             args.disk_size, deploy_steps)


if __name__ == '__main__':
    main(sys.argv)
