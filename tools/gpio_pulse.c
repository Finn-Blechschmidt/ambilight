/* Measures pulse widths on one GPIO pin without root (needs the gpio group).
 * WS2812B at 800 kHz: bit period 1.25 us, "0" bit high ~0.4 us, "1" bit high ~0.8 us.
 * Build: gcc -O2 -o gpio_pulse gpio_pulse.c      Usage: ./gpio_pulse [pin=18]
 * Resolution is limited by the register read time (a few 100 ns), so this is a plausibility check,
 * not a scope. */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

static inline uint64_t ticks(void) { uint64_t v; __asm__ volatile("mrs %0, cntvct_el0" : "=r"(v)); return v; }
static inline uint64_t freq(void) { uint64_t v; __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(v)); return v; }

int main(int argc, char **argv) {
    int pin = argc > 1 ? atoi(argv[1]) : 18;
    int fd = open("/dev/gpiomem", O_RDONLY | O_SYNC);
    if (fd < 0) { perror("gpiomem"); return 1; }
    volatile uint32_t *gpio = mmap(NULL, 4096, PROT_READ, MAP_SHARED, fd, 0);
    uint32_t mask = 1u << pin;
    double ns_per_tick = 1e9 / (double)freq();

    enum { N = 4000000 };
    uint64_t t_rise_prev = 0, t_rise = 0;
    int last = (gpio[0x34 / 4] & mask) != 0;
    int hist_hi[64] = {0}, hist_per[64] = {0};
    long reads = 0, pulses = 0;
    uint64_t t0 = ticks();
    for (long i = 0; i < N; i++) {
        int v = (gpio[0x34 / 4] & mask) != 0;
        reads++;
        if (v != last) {
            uint64_t t = ticks();
            if (v) {
                t_rise_prev = t_rise; t_rise = t;
                if (t_rise_prev) {
                    int b = (int)((t_rise - t_rise_prev) * ns_per_tick / 100);
                    if (b < 64) hist_per[b]++;
                }
            } else if (t_rise) {
                int b = (int)((t - t_rise) * ns_per_tick / 100);
                if (b < 64) hist_hi[b]++;
                pulses++;
            }
            last = v;
        }
    }
    double read_ns = (ticks() - t0) * ns_per_tick / reads;
    printf("pin %d: %ld reads, %.0f ns per read, %ld high pulses\n", pin, reads, read_ns, pulses);
    printf("high width histogram (100 ns bins):\n");
    for (int b = 0; b < 64; b++) if (hist_hi[b] > pulses / 100) printf("  %4d-%4d ns: %d\n", b * 100, b * 100 + 99, hist_hi[b]);
    printf("rise-to-rise histogram (100 ns bins):\n");
    for (int b = 0; b < 64; b++) if (hist_per[b] > pulses / 100) printf("  %4d-%4d ns: %d\n", b * 100, b * 100 + 99, hist_per[b]);
    return 0;
}
