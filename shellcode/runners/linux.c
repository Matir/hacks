#include <sys/mman.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/types.h>

#define SC_LENGTH 1024*1024

int debug_enabled = 0;

void debug(char *fmt, ...) {
  va_list ap;
  if (!debug_enabled)
    return;
  va_start(ap, fmt);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
}

int main(int argc, char **argv) {
  void *code;
  int r, total = 0;
  int fd = STDIN_FILENO;

  /* Setup the environment */
  debug_enabled = (getenv("DEBUG") != NULL) ? 1 : 0;
  code = mmap(NULL, SC_LENGTH, PROT_READ|PROT_WRITE|PROT_EXEC,
      MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
  if (code == MAP_FAILED) {
    fprintf(stderr, "Failed to allocate memory for mapping.\n");
    return 1;
  }
  debug("Allocated 0x%08x bytes at %p.  Send shellcode now.\n", SC_LENGTH, code);

  /* Check if we should read a file.
   * Yes, we could just mmap this file, but this has more code commonality.
   */
  if (argc > 1 && strcmp("-", argv[1])) {
    fd = open(argv[1], O_RDONLY);
    if (fd == -1) {
      fprintf(stderr, "Failed to open shellcode file (%s): %s\n",
          argv[1], strerror(errno));
      return 1;
    }
  }

  /* Read shellcode */
  while (1) {
    r = read(fd, code + total, SC_LENGTH - total);
    if (r <= 0) {
      break;
    }
    total += r;
  }
  if (!total) {
    debug("No shellcode read.  Aborting.\n");
    return 1;
  }

  /* Run shellcode */
  debug("Read 0x%08x bytes.  Executing.\n", total);
  ((void(*)())code)();
  return 0;
}
