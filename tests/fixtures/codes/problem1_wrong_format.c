#include <stdio.h>

int main(void) {
    int n;
    long long sum = 0;
    if (scanf("%d", &n) != 1) {
        return 1;
    }
    for (int i = 1; i <= n; i++) {
        sum += i;
    }
    /* 计算结果正确，但输出格式不符合题目要求 */
    printf("sum=%lld\n", sum);
    return 0;
}
