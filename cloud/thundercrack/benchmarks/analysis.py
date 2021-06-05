import pprint
import matplotlib
import matplotlib.pyplot as plt
import numpy as np


DEVICES = [
        'nvidia-tesla-k80',
        'nvidia-tesla-p100',
        'nvidia-tesla-p4',
        'nvidia-tesla-v100',
        'nvidia-tesla-t4',
        'nvidia-tesla-a100',
]

PRICES = {
        'nvidia-tesla-k80': 0.45,
        'nvidia-tesla-p100': 1.46,
        'nvidia-tesla-p4': 0.60,
        'nvidia-tesla-t4': 0.35,
        'nvidia-tesla-v100': 2.48,
        'nvidia-tesla-a100': 2.93,
}

MULTIPLIERS = {
        'GH/s': 1000*1000*1000,
        'MH/s': 1000*1000,
        'kH/s': 1000,
        'H/s': 1,
}

HASH_TYPES = {}


class Benchmarks:

    def __init__(self, name, results):
        self.name = name
        self.results = results

    def compute_normalized(self, baseline):
        norm = {}
        for k, v in self.results.items():
            norm[k] = v/baseline[k]
        self.normalized = norm
        return norm

    def score(self):
        return self.perf()/PRICES[self.name]

    def perf(self):
        tot = sum(self.normalized.values())
        return tot / len(self.normalized.values())

    @classmethod
    def load_benchmarks(cls, fname):
        cur_hash = None
        results = {}
        with open(fname) as fp:
            for line in fp:
                if line.startswith('Speed.#1'):
                    pieces = line.split()
                    speed = float(pieces[1])
                    speed *= MULTIPLIERS[pieces[2]]
                    results[cur_hash] = speed
                    continue
                elif line.startswith('Hashmode: '):
                    pieces = line.split()
                    cur_hash = int(pieces[1])
                    if cur_hash not in HASH_TYPES:
                        HASH_TYPES[cur_hash] = line.replace(
                                'Hashmode: ', '').strip()
        return cls(fname, results)

    @staticmethod
    def compute_baseline(across):
        mins = across[0].results.copy()
        for a in across:
            for k, v in a.results.items():
                if v < mins[k]:
                    mins[k] = v
        return mins


def format_speed(s):
    m = 0
    suffix = ''
    for k, v in MULTIPLIERS.items():
        if s/v > 1 and v > m:
            m = v
            suffix = k
    return '{:0.1f} {}'.format(s/m, suffix)


def do_graph(results):
    graph_modes = {
            0: 'MD5',
            100: 'SHA1',
            1000: 'NTLM',
            1800: 'sha512crypt',
            22000: 'WPA-PBKDF2',
    }
    group_size = 2
    width = (group_size-0.25)/len(DEVICES)
    ind = np.arange(1, len(graph_modes)*group_size, group_size)
    plt.clf()
    fig, ax = plt.subplots()
    ax.set_ylabel('Relative Speed')
    ax.set_title('Relative Speed by Device/Hash')
    for i, d in enumerate(DEVICES):
        vals = []
        for k in sorted(graph_modes.keys()):
            vals.append(results[d].normalized[k])
        offset = width*group_size*i/2-(width*group_size)
        ax.bar(ind + offset, vals, width, label=d)
    ax.set_xticks(ind)
    labels = []
    for k in sorted(graph_modes.keys()):
        labels.append(graph_modes[k])
    ax.set_xticklabels(labels)
    ax.legend()
    fig.tight_layout()
    #plt.show()
    plt.savefig('speeds.png')


def do_value_graph(results):
    graph_modes = {
            0: 'MD5',
            100: 'SHA1',
            1000: 'NTLM',
            1800: 'sha512crypt',
            22000: 'WPA-PBKDF2',
    }
    group_size = 2
    width = (group_size-0.25)/len(DEVICES)
    ind = np.arange(1, len(graph_modes)*group_size, group_size)
    plt.clf()
    fig, ax = plt.subplots()
    ax.set_ylabel('Relative Value')
    ax.set_title('Relative Value by Device/Hash')
    for i, d in enumerate(DEVICES):
        vals = []
        for k in sorted(graph_modes.keys()):
            vals.append(
                    results[d].normalized[k]/PRICES[d]*
                    PRICES['nvidia-tesla-k80'])
        offset = width*group_size*i/2-(width*group_size)
        ax.bar(ind + offset, vals, width, label=d)
    ax.set_xticks(ind)
    labels = []
    for k in sorted(graph_modes.keys()):
        labels.append(graph_modes[k])
    ax.set_xticklabels(labels)
    ax.legend()
    fig.tight_layout()
    #plt.show()
    plt.savefig('value.png')


def main():
    results = {}
    for d in DEVICES:
        results[d] = Benchmarks.load_benchmarks(d)
    baseline = Benchmarks.compute_baseline(list(results.values()))
    #pprint.pprint(results)
    #pprint.pprint(baseline)
    for v in results.values():
        v.compute_normalized(baseline)
        #pprint.pprint(v.normalized)
    for k, v in results.items():
        print('{:32}: {:0.2f}'.format(k, v.score()))
    with open('speeds.html', 'w') as fp:
        # Write headers
        fp.write('<table><thead><tr>')
        fp.write('<th>Algorithm</th>')
        for d in DEVICES:
            fp.write('<th colspan="2">{}</th>'.format(d))
        fp.write('</tr></thead>\n<tbody>\n')
        for k, v in HASH_TYPES.items():
            fp.write('<tr><td>{}</td>'.format(v))
            for d in DEVICES:
                fp.write('<td>{}</td><td>{:0.1f}%</td>'.format(
                        format_speed(results[d].results[k]),
                        results[d].normalized[k] * 100))
            fp.write('</tr>\n')
        fp.write('</tbody></table>\n')
    with open('values.html', 'w') as fp:
        fp.write(
                '<table><thead><tr><th>Card</th><th>Performance</th>'
                '<th>Price</th><th>Value</th></tr></thead>\n<tbody>\n')
        for k, v in results.items():
            fp.write(
                    ('<tr><td>{}</td><td>{:0.1f}</td>'
                        '<td>${:0.2f}</td><td>{:0.2f}</td></tr>\n').format(
                         k, v.perf()*100, PRICES[k],
                         v.score()*PRICES['nvidia-tesla-k80']))
        fp.write('</tbody></table>\n')
    do_graph(results)
    do_value_graph(results)


if __name__ == '__main__':
    main()
