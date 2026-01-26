#include "sa.hpp"
#include "baseline.hpp"
#include "hpwl.hpp"

#include <random>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <limits>

static double temp_schedule(int iter, int iters, double T0, double Tend)
{
    // exponential cooling
    double t = (double)iter / (double)iters;
    return T0 * std::pow(Tend / T0, t);
}

static bool accept_move(double delta, double T, std::mt19937 &rng)
{
    if (delta <= 0)
        return true;
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    double p = std::exp(-delta / T);
    return dist(rng) < p;
}

static std::vector<int> init_order_by_area(const Problem &P)
{
    std::vector<int> order = P.soft_ids;
    std::sort(order.begin(), order.end(),
              [&](int a, int b)
              {
                  return P.modules[a].min_area > P.modules[b].min_area;
              });
    return order;
}

static std::vector<int> neighbor_swap(std::vector<int> cur, std::mt19937 &rng)
{
    if (cur.size() < 2)
        return cur;
    std::uniform_int_distribution<int> dist(0, (int)cur.size() - 1);
    int i = dist(rng);
    int j = dist(rng);
    while (j == i)
        j = dist(rng);
    std::swap(cur[i], cur[j]);
    return cur;
}

static std::vector<int> neighbor_relocate(std::vector<int> cur, std::mt19937 &rng)
{
    if (cur.size() < 2)
        return cur;
    std::uniform_int_distribution<int> dist(0, (int)cur.size() - 1);
    int i = dist(rng);
    int j = dist(rng);
    while (j == i)
        j = dist(rng);

    int val = cur[i];
    cur.erase(cur.begin() + i);
    cur.insert(cur.begin() + j, val);
    return cur;
}

Solution place_sa(const Problem &P, const SAOptions &opt)
{
    // RNG
    int seed = opt.seed;
    if (seed == 0)
    {
        std::random_device rd;
        seed = (int)rd();
    }
    std::mt19937 rng(seed);

    // current state = area-desc order
    std::vector<int> cur_order = init_order_by_area(P);

    const double INF_COST = 1e18;

    auto decode_cost = [&](const std::vector<int> &order, Solution &out_sol) -> double
    {
        try
        {
            out_sol = decode_obstacle_aware(P, order); // ✅ SA 改 order 就會影響 layout
            return compute_total_hpwl(P, out_sol);
        }
        catch (const std::exception &)
        {
            // 這個順序無法合法放置，視為無效解
            return INF_COST;
        }
    };

    Solution cur_sol;
    double cur_cost = decode_cost(cur_order, cur_sol);

    // temperature auto set
    double T0 = opt.T0;
    double Tend = opt.Tend;
    if (T0 < 0)
        T0 = std::max(1.0, 0.05 * cur_cost);
    if (Tend < 0)
        Tend = std::max(1e-3, 1e-4 * cur_cost);

    std::cout << "[SA] seed=" << seed
              << " iters=" << opt.iters
              << " T0=" << T0
              << " Tend=" << Tend << "\n";
    std::cout << "[SA] init HPWL=" << cur_cost << "\n";

    // best
    std::vector<int> best_order = cur_order;
    Solution best_sol = cur_sol;
    double best_cost = cur_cost;

    std::uniform_real_distribution<double> pick(0.0, 1.0);

    int accepted = 0;
    for (int it = 1; it <= opt.iters; ++it)
    {
        double T = temp_schedule(it, opt.iters, T0, Tend);

        std::vector<int> nxt_order;
        if (pick(rng) < 0.70)
            nxt_order = neighbor_swap(cur_order, rng);
        else
            nxt_order = neighbor_relocate(cur_order, rng);

        Solution nxt_sol;
        double nxt_cost = decode_cost(nxt_order, nxt_sol);

        double delta = nxt_cost - cur_cost;
        if (accept_move(delta, T, rng))
        {
            cur_order = std::move(nxt_order);
            cur_sol = std::move(nxt_sol);
            cur_cost = nxt_cost;
            accepted++;

            if (cur_cost < best_cost)
            {
                best_cost = cur_cost;
                best_order = cur_order;
                best_sol = cur_sol;
            }
        }

        if (opt.log_every > 0 && (it % opt.log_every == 0))
        {
            double acc_rate = (double)accepted / (double)it;
            std::cout << "[SA] it=" << it
                      << " T=" << T
                      << " cur=" << cur_cost
                      << " best=" << best_cost
                      << " acc=" << acc_rate << "\n";
        }
    }

    std::cout << "[SA] done. best HPWL=" << best_cost << "\n";
    return best_sol;
}
