
#include "prime.h"
#include "hp_gfx.h"
#include "hp_input.h"
#include "hp_math.h"
#include "hp_string.h"

static void pd(const char *label, double v, int dec)
{
    char b[40];
    prints(label);
    ftoa(v, b, dec);
    prints(b);
    prints("\n");
}

int main(void) {
    hp_event ev;
    int w, h, x, key, frames = 0, t;
    if (!hp_gfx_init()) { printf("GFX INIT FAIL\n", 0, 0, 0, 0); return 1; }
    if (!hp_input_install()) { printf("INPUT HOOK FAIL\n", 0, 0, 0, 0); return 1; }
    w = hp_gfx_w(); h = hp_gfx_h();

    /* 直接画屏幕（静态图，无需 GROB 双缓冲 -> 省 307KB 堆）*/
    hp_clear(HP_BLACK);
    hp_text(4, 2, "TCC MATH LIB", HP_WHITE);
    hp_hline(0, 120, w, HP_GRAY);
    hp_vline(160, 0, h, HP_GRAY);
    for (x = 0; x < w; x++) {
        double v = hp_sin((double)(x - 160) / 40.0);
        int y = 120 - (int)(v * 80.0);
        hp_pixel(x, y, HP_GREEN);
    }

    pd("sin(0.5)=", hp_sin(0.5), 5);
    pd("cos(0.5)=", hp_cos(0.5), 5);
    pd("sqrt(2)=", hp_sqrt(2.0), 6);
    pd("exp(1)=", hp_exp(1.0), 6);
    pd("log(e)=", hp_log(HP_E), 6);
    pd("pow(2,10)=", hp_pow(2.0, 10.0), 1);
    pd("atan2(1,1)=", hp_atan2(1.0, 1.0), 6);
    printf("MATH_DONE\n", 0, 0, 0, 0);

    for (;;) {
        t = hp_poll_event(&ev);
        if (t == HP_EV_KEY) {
            key = hp_event_key(&ev);
            if (hp_event_key_down(&ev)) {
                printf("KEY %02x\n", key, 0, 0, 0);
                if (key == 0x51 || key == 0x01 || key == 0x83) {
                    hp_input_remove();
                    printf("MATH_EXIT %d\n", frames, 0, 0, 0);
                    return 0;
                }
            }
        }
        frames++;
        __sleep(16);
    }
}
