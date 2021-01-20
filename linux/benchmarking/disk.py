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
        self.speed = results['bw']
        self.iops = results['iops']

    def __str__(self):
        """Stringify"""
        ret = self.name
        if self.speed:
            ret += " {}k/s".format(self.speed)
            ret += " {}iops".format(self.iops)
        return ret


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
    runner.run()
    print(str(runner))


if __name__ == '__main__':
    main(sys.argv[1])
