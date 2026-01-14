#pragma once
#include <string>
#include "model.hpp"
#include "solution.hpp"

// Official output format:
// HPWL <wirelength>
// SOFTMODULE <n_soft>
// <soft_name> <num_corners>
// <x y>  (one corner per line, clockwise)
void write_solution(const Problem &P, const Solution &S,
                    const std::string &out_path, double hpwl);
