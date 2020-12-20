#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <stdlib.h>
#include <errno.h>

int verbose = 0;
int dryrun = 0;
char buf[2048];

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "Usage: %s [-v] [-d] <path>\n", argv[0]);
    return 1;
  }

  uid_t uid = getuid();
  gid_t gid = getgid();

  if (setresuid(0, 0, 0) != 0) {
    perror("setresuid");
    return 1;
  }

  if (setresgid(0, 0, 0) != 0) {
    perror("setresgid");
    return 1;
  }

  for(int i=1;i<argc;i++) {
    if (!strcmp("-v", argv[i])) {
      verbose = 1;
    } else if (!strcmp("-d", argv[i])) {
      dryrun = 1;
    } else {
      snprintf(buf, sizeof(buf), "chown -R %d:%d %s", uid, gid, argv[i]);
      if (verbose || dryrun) {
        fprintf(stderr, "%s\n", buf);
      }
      if (!dryrun) {
        system(buf);
      }
    }
  }
  return 0;
}
