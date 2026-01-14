#pragma once
#include <string>
#include "model.hpp"
#include "solution.hpp"

// Throws std::runtime_error with a clear message if illegal.
void check_solution_or_throw(const Problem &P, const Solution &S);
