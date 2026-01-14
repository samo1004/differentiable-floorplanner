#include "hpwl.hpp"
#include <cmath>

static inline double cx(const Rect &r) { return r.x + r.w / 2.0; }
static inline double cy(const Rect &r) { return r.y + r.h / 2.0; }

double compute_total_hpwl(const Problem &P, const Solution &S)
{
    double total = 0.0;
    for (const auto &e : P.edges)
    {
        const Rect &a = S.rect(e.u);
        const Rect &b = S.rect(e.v);
        double dist = std::abs(cx(a) - cx(b)) + std::abs(cy(a) - cy(b));
        total += dist * (double)e.w;
    }
    return total;
}
