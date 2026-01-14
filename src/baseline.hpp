#pragma once
#include "model.hpp"
#include "solution.hpp"

// Baseline placer:
// - pick a rectangle (w,h) for each soft module (area >= min_area, aspect ratio within [0.5, 2])
// - row packing left->right, bottom->top
// - try to avoid fixed by shifting x; if fails, fallback to ignoring fixed (to always output)
Solution place_row_packing_baseline(const Problem &P);
