#define _GNU_SOURCE

#include <link.h>
#include <stdio.h>
#include <elf.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>

#define DEBUG printf

typedef struct _sym_entry {
  struct _sym_entry *next;
  const char *name;
  void *ptr;
} sym_entry;

sym_entry *sym_head = NULL;

int phdr_callback(struct dl_phdr_info *info, size_t size, void *data);
const char *pt_type_str(uint32_t type);
int parse_dynamic_section(const ElfW(Phdr) *, void *, void *);
int parse_symbol_table(const ElfW(Sym) *symtab, size_t symtab_sz, const char *strtab, void *base_addr);
int main_done();

int main(int argc, char **argv) {
  dl_iterate_phdr(&phdr_callback, NULL);
  main_done();
  return 0;
}

int main_done() {
  return 1;
}

void add_symbol(const char *name, void *ptr) {
#ifndef SKIP_DUPE_CHECK
  sym_entry *p = sym_head;
  while (p) {
    if (!strcmp(name, p->name)) {
      printf("!!!Dupe symbol %s: %p -> %p\n", name, p->ptr, ptr);
    }
    p = p->next;
  }
#endif
  sym_entry *e = malloc(sizeof(sym_entry));
  e->next = sym_head;
  e->name = name;
  e->ptr = ptr;
  sym_head = e;
}

int phdr_callback(struct dl_phdr_info *info, size_t size, void *data) {
  printf("%p: %s\n", info->dlpi_addr, info->dlpi_name);
  for (uint16_t hdr=0;hdr < info->dlpi_phnum;hdr++) {
    const ElfW(Phdr) *cur_hdr = &info->dlpi_phdr[hdr];
    printf("  %02d: %s\n", hdr, pt_type_str(cur_hdr->p_type));
    if (cur_hdr->p_type == PT_DYNAMIC) {
      void *section_vaddr = (void *)info->dlpi_addr + cur_hdr->p_vaddr;
      parse_dynamic_section(cur_hdr, section_vaddr, (void *)info->dlpi_addr);
    }
  }
  return 0;
}

int parse_dynamic_section(const ElfW(Phdr) *sect, void *section_vaddr, void *base_addr) {
  ElfW(Dyn) *start = (ElfW(Dyn) *)section_vaddr;
  ElfW(Addr) *symtab = NULL;
  ElfW(Addr) *symtab_end = NULL;
  ElfW(Addr) *strtab = NULL;
  int items = sect->p_memsz / sizeof(ElfW(Dyn));
  for (int i=0; i<items; i++) {
    int tag = start[i].d_tag;
    if (tag == DT_SYMTAB) {
      symtab = (ElfW(Addr) *)start[i].d_un.d_ptr;
    } else if (tag == DT_STRTAB) {
      strtab = (ElfW(Addr) *)start[i].d_un.d_ptr;
    }
  }
  if (!symtab || (void *)symtab < (void *)0x1000) {
    return 1;
  }
  for (int i=0; i<items; i++) {
    int tag = start[i].d_tag;
    // Guess that next address is end
    if (tag == DT_PLTGOT || tag == DT_HASH || tag == DT_STRTAB ||
        tag == DT_RELA || tag == DT_RELA || tag == DT_INIT ||
        tag == DT_INIT || tag == DT_FINI || tag == DT_REL ||
        tag == DT_DEBUG || tag == DT_JMPREL || tag == DT_INIT_ARRAY ||
        tag == DT_FINI_ARRAY) {
      ElfW(Addr) *p = (ElfW(Addr) *)start[i].d_un.d_ptr;
      if (p < symtab)
        continue;
      if (symtab_end && p > symtab_end)
        continue;
      symtab_end = (ElfW(Addr) *)start[i].d_un.d_ptr;
    }
  }
  DEBUG("  symtab: %p\n", symtab);
  DEBUG("  symtab_end: %p\n", symtab_end);
  DEBUG("  strtab: %p\n", strtab);
  parse_symbol_table(
      (const ElfW(Sym) *)symtab,
      (void *)symtab_end - (void *)symtab,
      (const char *)strtab,
      base_addr);
  return 0;
}

int parse_symbol_table(const ElfW(Sym) *symtab, size_t symtab_sz, const char *strtab, void *base_addr) {
  int n_syms = symtab_sz / sizeof(ElfW(Sym));
  for (int i=0; i<n_syms; i++) {
    const ElfW(Sym) *entry = &(symtab[i]);
    ElfW(Half) shndx = entry->st_shndx;
    ElfW(Addr) addr = entry->st_value;
    const char *name = &strtab[entry->st_name];
    DEBUG("    \"%s\" -> (%d, %p)\n", name, shndx, addr);
    if (shndx == 0 || shndx >= 0xff00)
      continue;
    // Technically, shndx should be used to find the section, but this seems
    // to work in practice.
    void *sym_addr = base_addr + (size_t)addr;
    printf("    %p: %s\n", sym_addr, name);
    add_symbol(name, sym_addr);
    // Testing
    void *rtld_sym = dlsym(RTLD_DEFAULT, name);
    if (rtld_sym != sym_addr) {
      printf("!!!Mismatch: %s %p != %p\n", name, sym_addr, rtld_sym);
    }
  }
  return 0;
}

const char *pt_type_str(uint32_t type) {
  switch(type) {
    case PT_NULL:
      return "NULL";
    case PT_LOAD:
      return "LOAD";
    case PT_DYNAMIC:
      return "DYNAMIC";
    case PT_INTERP:
      return "INTERP";
    case PT_NOTE:
      return "NOTE";
    case PT_SHLIB:
      return "SHLIB";
    case PT_PHDR:
      return "PHDR";
  }
  return "UNKNOWN";
}
