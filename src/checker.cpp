#include "checker.hpp"
#include <stdexcept>
#include <sstream>
#include <cmath>

static void fail(const std::string &msg)
{
    throw std::runtime_error("CheckError: " + msg);
}

static inline long long area_ll(const Rect &r)
{
    return 1LL * r.w * r.h;
}

static void check_in_chip(const Problem &P, const Module &m, const Rect &r)
{
    if (r.x < 0 || r.y < 0)
    {
        fail(m.name + " has negative coordinate.");
    }
    if (r.x2() > P.chip_w || r.y2() > P.chip_h)
    {
        std::ostringstream oss;
        oss << m.name << " out of chip: rect=(" << r.x << "," << r.y << "," << r.w << "," << r.h
            << "), chip=(" << P.chip_w << "," << P.chip_h << ")";
        fail(oss.str());
    }
}

static void check_soft_constraints(const Module &m, const Rect &r)
{
    // area >= min_area
    if (area_ll(r) < m.min_area)
    {
        std::ostringstream oss;
        oss << m.name << " area too small: area=" << area_ll(r) << " < min_area=" << m.min_area;
        fail(oss.str());
    }
    // 0.5 <= h/w <= 2  <=>  h*2 >= w and h <= 2*w
    if (2LL * r.h < r.w || 1LL * r.h > 2LL * r.w)
    {
        std::ostringstream oss;
        oss << m.name << " aspect ratio violated: w=" << r.w << ", h=" << r.h
            << " (require 0.5 <= h/w <= 2)";
        fail(oss.str());
    }
}

void check_solution_or_throw(const Problem &P, const Solution &S)
{
    if ((int)S.rects.size() != P.n())
    {
        fail("Solution.rects size mismatch.");
    }

    // 1) soft in chip + constraints
    for (int sid : P.soft_ids)
    {
        const auto &m = P.modules[sid];
        const Rect &r = S.rect(sid);
        check_in_chip(P, m, r);
        if (r.w <= 0 || r.h <= 0)
            fail(m.name + " has non-positive w/h.");
        check_soft_constraints(m, r);
    }

    // 2) soft-fixed overlap
    for (int sid : P.soft_ids)
    {
        const Rect &sr = S.rect(sid);
        const std::string &sname = P.modules[sid].name;
        for (int fid : P.fixed_ids)
        {
            const Rect &fr = P.modules[fid].fixed_rect;
            if (overlap_area_positive(sr, fr))
            {
                fail("Overlap soft-fixed: " + sname + " overlaps " + P.modules[fid].name);
            }
        }
    }

    // 3) soft-soft overlap (O(n^2) is fine for now; later we can accelerate)
    for (size_t i = 0; i < P.soft_ids.size(); ++i)
    {
        int a = P.soft_ids[i];
        const Rect &ra = S.rect(a);
        for (size_t j = i + 1; j < P.soft_ids.size(); ++j)
        {
            int b = P.soft_ids[j];
            const Rect &rb = S.rect(b);
            if (overlap_area_positive(ra, rb))
            {
                fail("Overlap soft-soft: " + P.modules[a].name + " overlaps " + P.modules[b].name);
            }
        }
    }
}
