#include <stdio.h>

int main(void) {
    int n;
    if (scanf("%d", &n) != 1) {
        return 1;
    }
    /* 无边界地持续输出，用于验证输出大小限制 */
    for (;;) {
        printf("0123456789");
    }
    return 0;
}
