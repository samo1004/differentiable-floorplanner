#pragma once
#include "model.hpp"
#include "solution.hpp"

// Obstacle-aware baseline placer (avoids fixed + already placed soft rectangles).
Solution place_obstacle_aware_baseline(const Problem &P);
