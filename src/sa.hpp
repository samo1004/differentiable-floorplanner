#pragma once
#include "model.hpp"
#include "solution.hpp"

struct SAOptions
{
    int iters = 20000;    // SA iterations
    int seed = 0;         // 0 => random_device
    double T0 = -1.0;     // <0 => auto
    double Tend = -1.0;   // <0 => auto
    int log_every = 2000; // print progress
};

Solution place_sa(const Problem &P, const SAOptions &opt);
