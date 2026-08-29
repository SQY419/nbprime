/*
 * hp_input.h -- keyboard + touch input for TCC-compiled programs on the
 * HP Prime G1, via firmware get_event (svc 0x1003f).
 *
 * Event structure (verified against the PureDOOM port's my_get_event_hook):
 *   ev->[4]   = event type:  0x00100010 = key,  15 = touch,  else = none
 *   key:      ev->[28] = 16 (press) / 0x100000 (release);  ev->[34] = u16
 *             physical scan code (see HP_KEY_* below)
 *   touch:    ev->[24] = u16 item count (<= 8); each item i occupies 12
 *             bytes at ev->[28 + 12*i]:  [0] = u32 item type (1 = press /
 *             abs position, 2 = move, 8 = release), [4] = u16 (0 = valid),
 *             [6] = u16 x, [8] = u16 y
 *
 * Usage:
 *     hp_event ev;
 *     int t = hp_poll_event(&ev);
 *     if (t == HP_EV_KEY) { int k = hp_event_key(&ev); ... }
 *     if (t == HP_EV_TOUCH) { int x, y; hp_event_touch(&ev, 0, &x, &y); }
 */
#ifndef HP_INPUT_H
#define HP_INPUT_H

#define HP_EV_NONE   0
#define HP_EV_KEY    0x00100010
#define HP_EV_TOUCH  15

#define HP_EV_KEY_DOWN  16
#define HP_EV_KEY_UP    0x100000

#define HP_TOUCH_PRESS    1
#define HP_TOUCH_MOVE     2
#define HP_TOUCH_RELEASE  8

typedef struct hp_event {
    unsigned data[32];      /* 128 bytes, opaque (firmware fills it) */
} hp_event;

/* poll one event (non-blocking); returns HP_EV_KEY / HP_EV_TOUCH / 0.
 * Requires hp_input_install() first: input arrives via the firmware
 * get_event hook (DOOM-port style), NOT by calling get_event directly
 * (it blocks on the OS UI thread). */
int hp_poll_event(hp_event *ev);

/* install the get_event hook: patches the firmware API slot
 * 0x307fbfa0 so the OS event loop feeds our queue.  Call once at start.
 * Returns 1 on success, 0 if the slot is already patched. */
int  hp_input_install(void);
/* restore the firmware slot.  Call before exiting so the calculator's
 * own UI keeps working afterwards.  NOTE: this is NOT done automatically
 * at exit -- forgetting it leaves the hook installed until reboot. */
void hp_input_remove(void);
/* 1 while the hook is installed; 1 while the OS thread is inside the
 * hook's blocking get_event call. */
int  hp_input_hooked(void);
int  hp_input_busy(void);

/* key events */
int hp_event_key(const hp_event *ev);        /* physical scan code (the key id) */
int hp_event_key_down(const hp_event *ev);   /* 1 = press, 0 = release */

/* touch events */
int hp_event_touch_count(const hp_event *ev);
/* item type (HP_TOUCH_*) or 0; fills x/y (screen pixels) */
int hp_event_touch(const hp_event *ev, int i, int *x, int *y);

/* ---- physical scan codes (HP Prime G1 keyboard, from the DOOM port) ---- */
#define HP_KEY_ESC       0x01
#define HP_KEY_LEFT      0x02
#define HP_KEY_UP        0x03
#define HP_KEY_RIGHT     0x04
#define HP_KEY_DOWN      0x05
#define HP_KEY_BACKSPACE 0x0C
#define HP_KEY_ENTER     0x0D
#define HP_KEY_SPACE     0x20
#define HP_KEY_ON        0x83   /* ON/Cancel */
#define HP_KEY_SHIFT     0x8B
#define HP_KEY_F1        0x91
#define HP_KEY_F2        0x93
#define HP_KEY_F3        0xB2
#define HP_KEY_F4        0xB3
#define HP_KEY_F5        0xB4
#define HP_KEY_F6        0xB5
#define HP_KEY_ALPHA     0xB6
#define HP_KEY_PLUSMINUS 0x4D
#define HP_KEY_X2        0x4C

#endif /* HP_INPUT_H */
