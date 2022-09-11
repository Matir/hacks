#!/usr/bin/env python3

import bs4
import os
import pathlib
import re
import subprocess
import sys

DRY_RUN = False
FFMPEG = "/usr/bin/ffmpeg"
OUTDIR = "movies.fixed"


def rename_and_title(infile, outfile, title):
    outfile = str(pathlib.Path(OUTDIR).joinpath(outfile))
    cmd = [
            FFMPEG,
            "-i", infile,
            "-codec", "copy",
            "-metadata", "Title={}".format(title),
            outfile]
    print('"' + '" "'.join(cmd) + '"')
    if DRY_RUN:
        return
    subprocess.run(cmd, check=True)


def find_links(bs):
    links = [x for x in bs.find_all('a') if 'title' in x.get('class', [])]
    res = []
    for l in links:
        print(l.get('href'), l.text.strip())
        res.append((l.get('href'), l.text.strip()))
    return res


def slugify(name):
    name = name.lower()
    return re.sub('[^a-z0-9]+', '-', name)


def main(argv):
    name = 'Start Here.html'
    if len(argv) > 1:
        name = argv[1]
    with open(name) as fp:
        links = find_links(bs4.BeautifulSoup(fp, features='lxml'))
    os.makedirs(OUTDIR, exist_ok=True)
    for infile, title in links:
        p = pathlib.Path(infile)
        outfile = p.stem + '-' + slugify(title)[:128] + p.suffix
        rename_and_title(infile, outfile, title)


if __name__ == '__main__':
    main(sys.argv)
