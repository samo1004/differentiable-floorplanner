#include "baseline.hpp"
#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <unordered_set>

// ---------------------------
// Helpers
// ---------------------------
static inline long long area_ll(int w, int h)
{
    return 1LL * w * h;
}

static bool aspect_ok(int w, int h)
{
    // 0.5 <= h/w <= 2  <=> 2h >= w and h <= 2w
    return (2LL * h >= w) && (1LL * h <= 2LL * w);
}

static void add_shape(std::vector<std::pair<int, int>> &shapes, int A, int w, int h)
{
    if (w <= 0 || h <= 0)
        return;
    if (area_ll(w, h) < A)
        return;
    if (!aspect_ok(w, h))
        return;

    for (auto &p : shapes)
    {
        if (p.first == w && p.second == h)
            return;
    }
    shapes.push_back({w, h});
}

static std::vector<std::pair<int, int>> gen_shapes(int A)
{
    std::vector<std::pair<int, int>> shapes;
    if (A <= 0)
    {
        shapes.push_back({1, 1});
        return shapes;
    }

    // 1) near-square
    int w1 = std::max(1, (int)std::ceil(std::sqrt((double)A)));
    int h1 = (A + w1 - 1) / w1;
    add_shape(shapes, A, w1, h1);
    add_shape(shapes, A, h1, w1);

    // 2) wider
    int w2 = std::max(1, (int)std::ceil(std::sqrt(2.0 * A)));
    int h2 = (A + w2 - 1) / w2;
    add_shape(shapes, A, w2, h2);
    add_shape(shapes, A, h2, w2);

    // 3) taller-ish
    int w3 = std::max(1, (int)std::ceil(std::sqrt(0.5 * A)));
    int h3 = (A + w3 - 1) / w3;
    add_shape(shapes, A, w3, h3);
    add_shape(shapes, A, h3, w3);

    // fallback
    if (shapes.empty())
        add_shape(shapes, A, w1, h1);
    return shapes;
}

static bool overlaps_any(const Rect &r, const std::vector<Rect> &obstacles, int &max_y2)
{
    bool hit = false;
    int m = -1;
    for (const auto &o : obstacles)
    {
        if (overlap_area_positive(r, o))
        {
            hit = true;
            m = std::max(m, o.y2());
        }
    }
    if (hit)
        max_y2 = m;
    return hit;
}

// For a fixed x,w,h, compute the minimum y >= 0 such that rect does NOT overlap obstacles.
// Return y if feasible, or INF if not feasible.
static int drop_y(const Problem &P, int x, int w, int h, const std::vector<Rect> &obstacles)
{
    const int INF = 1e9;
    int y = 0;

    // progress guard: y must strictly increase when overlapping
    for (int iter = 0; iter <= (int)obstacles.size(); ++iter)
    {
        if (y + h > P.chip_h)
            return INF;

        Rect cand{x, y, w, h};
        int max_y2 = -1;
        if (!overlaps_any(cand, obstacles, max_y2))
        {
            return y; // legal at this x
        }

        if (max_y2 <= y)
        {
            // Should not happen, but safety
            return INF;
        }
        y = max_y2;
    }
    return INF;
}

static std::vector<int> gen_x_candidates(const Problem &P, int w, const std::vector<Rect> &obstacles)
{
    std::vector<int> xs;
    xs.reserve(obstacles.size() * 2 + 4);
    xs.push_back(0);
    xs.push_back(std::max(0, P.chip_w - w));

    for (const auto &o : obstacles)
    {
        xs.push_back(o.x2());  // place to the right of obstacle
        xs.push_back(o.x - w); // place to the left of obstacle
    }

    // keep only valid range
    std::vector<int> out;
    out.reserve(xs.size());
    for (int x : xs)
    {
        if (x < 0)
            continue;
        if (x + w > P.chip_w)
            continue;
        out.push_back(x);
    }

    std::sort(out.begin(), out.end());
    out.erase(std::unique(out.begin(), out.end()), out.end());
    return out;
}

// ---------------------------
// Main baseline: obstacle-aware placement
// ---------------------------
Solution place_obstacle_aware_baseline(const Problem &P)
{
    Solution sol;
    sol.rects.resize(P.n());

    // Obstacles start with fixed rects
    std::vector<Rect> obstacles;
    obstacles.reserve(P.fixed_ids.size() + P.soft_ids.size());

    for (int fid : P.fixed_ids)
    {
        Rect fr = P.modules[fid].fixed_rect;
        sol.rects[fid] = fr;
        obstacles.push_back(fr);
    }

    // Place larger soft modules first (more robust)
    std::vector<int> order = P.soft_ids;
    std::sort(order.begin(), order.end(),
              [&](int a, int b)
              {
                  return P.modules[a].min_area > P.modules[b].min_area;
              });

    for (int sid : order)
    {
        const auto &m = P.modules[sid];
        int A = m.min_area;

        auto shapes = gen_shapes(A);

        bool placed = false;
        Rect best;
        int best_y = 1e9;
        int best_x = 1e9;

        for (auto [w, h] : shapes)
        {
            if (w > P.chip_w || h > P.chip_h)
                continue;

            auto xs = gen_x_candidates(P, w, obstacles);
            for (int x : xs)
            {
                int y = drop_y(P, x, w, h, obstacles);
                if (y >= 1000000000)
                    continue;

                // pick lowest y, then lowest x
                if (y < best_y || (y == best_y && x < best_x))
                {
                    best_y = y;
                    best_x = x;
                    best = Rect{x, y, w, h};
                    placed = true;
                }
            }
        }

        if (!placed)
        {
            throw std::runtime_error("BaselinePlaceError: cannot place soft module '" + m.name + "' legally.");
        }

        sol.rects[sid] = best;
        obstacles.push_back(best);
    }

    return sol;
}
