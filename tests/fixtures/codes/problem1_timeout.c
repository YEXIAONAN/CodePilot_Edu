#include <stdio.h>

int main(void) {
    volatile int keep_running = 1;
    while (keep_running) {
        /* 故意死循环，用于验证时间限制 */
    }
    return 0;
}
