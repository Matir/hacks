#!/usr/bin/env python3

import json
import os
import subprocess
import sys


def debug_json(data):
    json.dump(data, sys.stdout, sort_keys=True, indent=2)


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
                'end_fsync': 1,
        }
        self.jobs = {}

    def addjob(self, job):
        self.jobs[job.name] = job

    def run(self):
        args = ['--{}={}'.format(k, v) for k, v in self.args.items()]
        args += ['--group_reporting']
        success = True
        for j in self.jobs.values():
            try:
                if not j.run(self.fio_path, args):
                    success = False
            finally:
                try:
                    os.unlink(self.filename)
                except Exception as ex:
                    print('Error unlinking:', ex)
        return success

    def __str__(self):
        return '\n'.join(str(j) for j in self.jobs.values())


class FIOJob(object):

    def __init__(self, name, size=4096, op='read', iodepth=1, threads=1):
        assert(op in ('read', 'write', 'randread', 'randwrite'))
        self.name = name
        self.size = size
        self.op = op
        self.iodepth = iodepth
        self.speed = None
        self.iops = None
        self.threads = threads

    @property
    def args(self):
        return [
                '--new_group',
                '--name={}'.format(self.name),
                '--bs={}'.format(self.size),
                '--rw={}'.format(self.op),
                '--iodepth={}'.format(self.iodepth),
                '--numjobs={}'.format(self.threads),
        ]

    def run(self, fio_path, base_args=[]):
        args = [fio_path]
        args.extend(base_args)
        args.extend(self.args)
        print('Command: {}'.format(' '.join(args)))
        sys.stdout.flush()
        cp = subprocess.run(args, capture_output=True)
        if cp.returncode:
            print('Error running!')
            print(cp.stderr.decode('utf-8'))
            return False
        results = json.loads(cp.stdout)
        if len(results['jobs']) != 1:
            print('Expected only one result!')
            debug_json(results)
            return False
        self.load_results(results['jobs'][0])
        return True

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
        'SEQ1M Q1T1 Read', size=1024*1024))
    runner.addjob(FIOJob(
        'SEQ1M Q1T1 Write', size=1024*1024, op='write'))
    runner.addjob(FIOJob(
        'SEQ1M Q8T1 Read', size=1024*1024, iodepth=8))
    runner.addjob(FIOJob(
        'SEQ1M Q8T1 Write', size=1024*1024, op='write', iodepth=8))
    runner.addjob(FIOJob(
        'RND4K Q32T1 Read', op='randread', iodepth=32))
    runner.addjob(FIOJob(
        'RND4K Q32T1 Write', op='randwrite', iodepth=32))
    runner.addjob(FIOJob(
        'RND4K Q32T16 Read', op='randread', iodepth=32, threads=16))
    runner.addjob(FIOJob(
        'RND4K Q32T16 Write', op='randwrite', iodepth=32, threads=16))
    if runner.run():
        print(str(runner))
        sys.stdout.flush()


if __name__ == '__main__':
    main(sys.argv[1])
