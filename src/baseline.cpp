#include "baseline.hpp"
#include <cmath>
#include <stdexcept>
#include <algorithm>

static Rect choose_soft_rect(int min_area)
{
    if (min_area <= 0)
        return Rect{0, 0, 1, 1};

    // For row-based packing, prefer wider rectangles to reduce row heights.
    // Start from w ~= sqrt(2A) (tends to give h/w ~ 0.5), then adjust to satisfy:
    //   area >= A and 0.5 <= h/w <= 2
    int w = std::max(1, (int)std::floor(std::sqrt(2.0 * min_area)));
    int h = (min_area + w - 1) / w;

    // If too wide (h/w < 0.5), decrease w until ratio ok.
    while (2LL * h < w)
    {
        --w;
        if (w <= 0)
        {
            w = 1;
            break;
        }
        h = (min_area + w - 1) / w;
    }

    // If too tall (h/w > 2), increase w.
    while ((long long)h > 2LL * w)
    {
        ++w;
        h = (min_area + w - 1) / w;
    }

    // Final safety: ensure area >= min_area.
    while ((long long)w * h < min_area)
        ++h;

    return Rect{0, 0, w, h};
}

static bool overlap_with_any_fixed(const Problem &P, const Rect &r, int &blocking_x2)
{
    bool hit = false;
    int max_x2 = -1;
    for (int fid : P.fixed_ids)
    {
        const Rect &fr = P.modules[fid].fixed_rect;
        if (overlap_area_positive(r, fr))
        {
            hit = true;
            max_x2 = std::max(max_x2, fr.x2());
        }
    }
    if (hit)
        blocking_x2 = max_x2;
    return hit;
}

static Solution place_impl(const Problem &P, bool avoid_fixed)
{
    Solution sol;
    sol.rects.resize(P.n());

    // Fixed rects are known.
    for (int fid : P.fixed_ids)
        sol.rects[fid] = P.modules[fid].fixed_rect;

    int x = 0, y = 0, row_h = 0;

    for (int sid : P.soft_ids)
    {
        Rect r = choose_soft_rect(P.modules[sid].min_area);

        if (r.w > P.chip_w || r.h > P.chip_h)
        {
            throw std::runtime_error("BaselinePlaceError: a soft module is larger than the chip.");
        }

        while (true)
        {
            if (x + r.w > P.chip_w)
            {
                // 沒放進任何東西就換行 => row_h 會是 0，y 不會動，會卡死
                if (row_h == 0)
                {
                    throw std::runtime_error(
                        "BaselinePlaceError: row blocked by fixed obstacles (no progress).");
                }
                x = 0;
                y += row_h;
                row_h = 0;
                continue;
            }
            if (y + r.h > P.chip_h)
            {
                throw std::runtime_error("BaselinePlaceError: cannot fit all soft modules inside chip.");
            }

            Rect cand = r;
            cand.x = x;
            cand.y = y;

            if (avoid_fixed)
            {
                int block_x2 = -1;
                if (overlap_with_any_fixed(P, cand, block_x2))
                {
                    x = std::max(x, block_x2);
                    continue;
                }
            }

            sol.rects[sid] = cand;
            x += cand.w;
            row_h = std::max(row_h, cand.h);
            break;
        }
    }

    return sol;
}

Solution place_row_packing_baseline(const Problem &P)
{
    // Pass 1: try to avoid fixed obstacles.
    try
    {
        return place_impl(P, /*avoid_fixed=*/true);
    }
    catch (...)
    {
        // Pass 2: ignore fixed to ensure we can always produce an output file.
        return place_impl(P, /*avoid_fixed=*/false);
    }
}
