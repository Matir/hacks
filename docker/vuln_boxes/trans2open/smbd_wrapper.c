#include <sys/personality.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>

int main(int argc, char **argv) {
  pid_t child_pid = fork();
  if (child_pid == -1) {
    printf("Fork failed!\n");
    return 1;
  }
  if (!child_pid) {
    int pers = personality(ADDR_NO_RANDOMIZE | PER_LINUX32_3GB);
    if (pers == -1) {
      printf("Personality failed!\n");
      perror("Failure:");
      return 1;
    }
    char *argv[] = {"smbd", "-D", NULL};
    execv("/usr/local/samba/bin/smbd", argv);
    printf("Execv failed!\n");
    return 1;
  }
  while(1) sleep(3600);
}
