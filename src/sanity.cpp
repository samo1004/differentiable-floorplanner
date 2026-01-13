#include "sanity.hpp"
#include <stdexcept>

static bool inside_chip(const Problem& P, const Rect& r) {
    return r.x >= 0 && r.y >= 0 && r.x + r.w <= P.chip_w && r.y + r.h <= P.chip_h;
}

void sanity_check_fixed(const Problem& P, const std::string& file) {
    // fixed inside chip
    for (int idx = 0; idx < (int)P.fixed_ids.size(); ++idx) {
        int id = P.fixed_ids[idx];
        const Rect& r = P.modules[id].fixed_rect;

        if (r.w <= 0 || r.h <= 0) {
            throw std::runtime_error("SanityError[file=" + file + "][FIXEDMODULE #" + std::to_string(idx+1) +
                                     "]: non-positive w/h");
        }
        if (!inside_chip(P, r)) {
            throw std::runtime_error("SanityError[file=" + file + "][FIXEDMODULE #" + std::to_string(idx+1) +
                                     "]: fixed rect out of chip");
        }
    }

    // fixed no positive-area overlap
    for (int i = 0; i < (int)P.fixed_ids.size(); ++i) {
        for (int j = i + 1; j < (int)P.fixed_ids.size(); ++j) {
            const Rect& a = P.modules[P.fixed_ids[i]].fixed_rect;
            const Rect& b = P.modules[P.fixed_ids[j]].fixed_rect;
            if (overlap_area_positive(a, b)) {
                throw std::runtime_error("SanityError[file=" + file + "]: fixed modules overlap (positive area)");
            }
        }
    }
}
