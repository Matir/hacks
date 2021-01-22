#!/usr/bin/env python3

import json
import subprocess
import sys


class FIORunner(object):

    def __init__(
            self, test_filename, size="1000m", loops=5,
            fio_path='/usr/bin/fio'):
        self.fio_path = fio_path
        self.filename = test_filename
        self.args = {
                'output-format': 'json',
                'ioengine': 'libaio',
                'direct': 1,
                'filename': test_filename,
                'size': size,
                'loops': str(loops),
        }
        self.jobs = {}

    def addjob(self, job):
        self.jobs[job.name] = job

    def run(self):
        args = ['--{}={}'.format(k, v) for k, v in self.args.items()]
        args = [self.fio_path] + args
        for j in self.jobs.values():
            args.extend(j.args)
        print('Command: {}'.format(' '.join(args)))
        cp = subprocess.run(args, capture_output=True)
        if cp.returncode:
            print('Error running!')
            print(cp.stderr.decode('utf-8'))
            return False
        results = json.loads(cp.stdout)
        for j in results['jobs']:
            self.jobs[j['jobname']].load_results(j)
        return True

    def __str__(self):
        return '\n'.join(str(j) for j in self.jobs.values())


class FIOJob(object):

    def __init__(self, name, size=4096, op='read', iodepth=1):
        assert(op in ('read', 'write', 'randread', 'randwrite'))
        self.name = name
        self.size = size
        self.op = op
        self.iodepth = iodepth
        self.speed = None
        self.iops = None

    @property
    def args(self):
        return [
                '--name={}'.format(self.name),
                '--bs={}'.format(self.size),
                '--rw={}'.format(self.op),
                '--iodepth={}'.format(self.iodepth),
        ]

    def load_results(self, json_data):
        """Load relevant JSON properties."""
        results = json_data['write' if 'write' in self.op else 'read']
        self.speed = results['bw']*1024.0  # results in k
        self.iops = results['iops']

    def __str__(self):
        """Stringify"""
        if self.speed:
            return "{:20s} {:>10s}/s  {:5.0f} iops".format(
                    self.name,
                    self.format_bytes(self.speed),
                    self.iops)
        return self.name

    @staticmethod
    def format_bytes(n):
        exts = ["", "k", "M", "G", "T"]
        for e in exts:
            if n >= 1024:
                n /= 1024.0
                continue
            break
        return "{:0.2f}{}B".format(n, e)


def main(path):
    runner = FIORunner(path)
    runner.addjob(FIOJob(
        'Seqread', size=1024*1024))
    runner.addjob(FIOJob(
        'Seqwrite', size=1024*1024, op='write'))
    runner.addjob(FIOJob(
        '512Kread', size=512*1024, op='randread'))
    runner.addjob(FIOJob(
        '512Kwrite', size=512*1024, op='randwrite'))
    runner.addjob(FIOJob(
        '4kQD32read', op='randread', iodepth=32))
    runner.addjob(FIOJob(
        '4kQD32write', op='randwrite', iodepth=32))
    if runner.run():
        print(str(runner))


if __name__ == '__main__':
    main(sys.argv[1])
