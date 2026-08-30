/*
 * prime.h -- user-facing header for TCC-compiled programs on the HP Prime.
 *
 * `#include "prime.h"` at the top of your C source.  The implementations
 * live in hp_rt.c (compiled on the calculator together with your code)
 * and rt_svc.o / rt_aeabi.o (prebuilt, linked by TCC).
 */
#ifndef PRIME_H
#define PRIME_H

typedef unsigned int size_t;
#define NULL ((void *)0)

/* console output -> PRIMELOG ring (main.py prints it).
 * NOTE: TCC's ARM backend has no varargs support, so printf takes a FIXED
 * four arguments:  printf(fmt, a0, a1, a2, a3);  pass 0 for unused ones.
 * Convenience helpers prints/printd/printx avoid format strings entirely. */
int  printf(const char *fmt, unsigned long a0, unsigned long a1,
            unsigned long a2, unsigned long a3);
int  sprintf(char *buf, const char *fmt, unsigned long a0, unsigned long a1,
             unsigned long a2, unsigned long a3);
int  puts(const char *s);
void prints(const char *s);
void printd(long v);
void printx(unsigned long v);

/* firmware syscalls (see rt_svc.o); num is one of:
 *   0x10037 malloc   0x10038 calloc   0x10039 realloc   0x1003a free
 *   0x1026f fopen    0x100ca fclose   0x100cf fseek    0x100d0 ftell
 *   0x100d4 fread    0x100d7 fwrite   0x100cb filesize
 *   0x10008 os_sleep 0x100a5 get_time 0x1008d get_lcd
 * Convention: push{r0}; push{lr}; svc N; result in r0.
 */
void  __sleep(unsigned ms);
unsigned long __gettime(void);

/* memory */
void *malloc(size_t n);
void *calloc(size_t n, size_t sz);
void  free(void *p);

/* strings / memory */
size_t strlen(const char *s);
int    strcmp(const char *a, const char *b);
int    strncmp(const char *a, const char *b, size_t n);
char  *strcpy(char *d, const char *s);
void  *memcpy(void *d, const void *s, size_t n);
void  *memset(void *d, int c, size_t n);
int    memcmp(const void *a, const void *b, size_t n);

#endif /* PRIME_H */
