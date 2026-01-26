#pragma once
#include "model.hpp"
#include "solution.hpp"

// Obstacle-aware baseline placer (avoids fixed + already placed soft rectangles).
Solution place_obstacle_aware_baseline(const Problem &P);
Solution decode_obstacle_aware(const Problem &P, const std::vector<int> &soft_order);
