#include <stdio.h>

int main(void) {
    int n;
    if (scanf("%d", &n) != 1) {
        return 1;
    }
    int *pointer = 0;
    *pointer = n; /* 空指针写入，触发运行异常 */
    printf("%d\n", n);
    return 0;
}
