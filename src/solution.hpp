#pragma once
#include <vector>
#include "model.hpp"

// Stores a concrete placement (and chosen shapes for soft modules).
// For now: one bounding rectangle per module (soft + fixed).
struct Solution
{
    std::vector<Rect> rects; // size == Problem.n()

    const Rect &rect(int id) const { return rects.at(id); }
    Rect &rect(int id) { return rects.at(id); }
};
