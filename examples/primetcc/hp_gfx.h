/*
 * hp_gfx.h -- graphics library for TCC-compiled programs on the HP Prime G1.
 *
 * The HP Prime G1 has a 320x240 LCD with a 32-bit ARGB framebuffer
 * (alpha byte ignored).  Access pattern (reverse-engineered from the
 * working gbemu port): call get_lcd (svc 0x1008d) -> r0 points to a
 * struct whose first word is another struct:  [2]=width (u16),
 * [4]=height (u16), [16]=framebuffer pointer (u32).  Pixels are 32-bit
 * words 0x00RRGGBB (write 0xFF000000 alpha like gbemu does).
 *
 * Usage in a TCC program:
 *     #include "prime.h"
 *     #include "hp_gfx.h"
 *     ...
 *     if (hp_gfx_init()) {
 *         hp_clear(HP_BLACK);
 *         hp_text(10, 10, "Hello!", HP_GREEN);
 *     }
 *
 * hp_gfx.c is compiled on the calculator together with your code.c and
 * hp_rt.c (add it to the TCC command line, see main.py).
 */
#ifndef HP_GFX_H
#define HP_GFX_H

#define HP_LCD_W 320
#define HP_LCD_H 240

/* default 5x8 font cell (font lives in hp_gfx.c) */
#define HP_FONT_W 5
#define HP_FONT_H 8

typedef unsigned int hp_color;

/* 0x00RRGGBB with 0xFF alpha (matches the Prime framebuffer) */
#define HP_RGB(r, g, b) \
    (0xFF000000u | (((unsigned)(r) & 0xFFu) << 16) | \
     (((unsigned)(g) & 0xFFu) << 8) | ((unsigned)(b) & 0xFFu))

#define HP_BLACK    HP_RGB(0, 0, 0)
#define HP_WHITE    HP_RGB(255, 255, 255)
#define HP_RED      HP_RGB(255, 0, 0)
#define HP_GREEN    HP_RGB(0, 255, 0)
#define HP_BLUE     HP_RGB(0, 0, 255)
#define HP_YELLOW   HP_RGB(255, 255, 0)
#define HP_CYAN     HP_RGB(0, 255, 255)
#define HP_MAGENTA  HP_RGB(255, 0, 255)
#define HP_ORANGE   HP_RGB(255, 165, 0)
#define HP_GRAY     HP_RGB(128, 128, 128)

/* call once before drawing; returns 1 on success, 0 if get_lcd failed */
int  hp_gfx_init(void);
int  hp_gfx_w(void);              /* LCD width in pixels (320) */
int  hp_gfx_h(void);              /* LCD height in pixels (240) */

/* primitives (coordinates are clipped, no error) */
void hp_pixel(int x, int y, hp_color c);
hp_color hp_get_pixel(int x, int y);
void hp_clear(hp_color c);
void hp_fill_rect(int x, int y, int w, int h, hp_color c);
void hp_rect(int x, int y, int w, int h, hp_color c);   /* outline */
void hp_hline(int x, int y, int w, hp_color c);
void hp_vline(int x, int y, int h, hp_color c);
void hp_line(int x0, int y0, int x1, int y1, hp_color c);  /* Bresenham */
void hp_circle(int cx, int cy, int r, hp_color c);         /* outline */

/* text: 5x8 fixed font, 6 px advance per char */
void hp_text(int x, int y, const char *s, hp_color c);
void hp_text_bg(int x, int y, const char *s, hp_color fg, hp_color bg);
int  hp_text_w(const char *s);    /* width in pixels */

/* filled shapes */
void hp_fill_circle(int cx, int cy, int r, hp_color c);

/* ---- GROB layer buffer (like the HP Prime's GROB) -----------------------
 * An off-screen bitmap you can draw into with the same primitives, then
 * blit to the screen in one go -- double buffering, no flicker.
 *
 *   hp_grob *g = hp_grob_new(320, 240);   // full-screen back buffer
 *   hp_grob_select(g);                    // draw into g (NULL = screen)
 *   hp_clear(HP_BLACK); hp_fill_circle(...); hp_text(...);
 *   hp_grob_select(NULL);                 // back to the screen
 *   hp_grob_blit(g, 0, 0);                // one blit -> screen
 *   hp_grob_free(g);
 */
typedef struct hp_grob {
    int w, h;
    unsigned *px;            /* w*h ARGB pixels */
} hp_grob;

hp_grob *hp_grob_new(int w, int h);
void     hp_grob_free(hp_grob *g);
void     hp_grob_select(hp_grob *g);      /* draw target; NULL = screen */
void     hp_grob_blit(hp_grob *g, int x, int y);   /* copy onto the screen */

#endif /* HP_GFX_H */
