// Two functions, a call, and logical operators
int square(int n) {
    return n * n;
}

int main() {
    int x = 2 + 3 * 4;
    int y = square(x);
    if (y > 100 && !(x == 0)) {
        printf("big: %d\n", y);
    }
    return 0;
}
