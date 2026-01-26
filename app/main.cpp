#include <iostream>
#include <algorithm>
#include <string>
#include <stdexcept>

#include "parser.hpp"
#include "sanity.hpp"
#include "baseline.hpp"
#include "hpwl.hpp"
#include "writer.hpp"
#include "checker.hpp"

// ✅ 新增：SA
#include "sa.hpp"

static bool is_flag(const char *s)
{
    return s && s[0] == '-' && s[1] == '-';
}

static void usage()
{
    std::cerr
        << "Usage:\n"
        << "  placer <case-input.txt> [out.txt] [--sa] [--iters N] [--seed N]\n"
        << "         [--log_every N] [--T0 X] [--Tend X] [--strict]\n"
        << "\nExamples:\n"
        << "  placer case01-input.txt\n"
        << "  placer case01-input.txt out.txt\n"
        << "  placer case01-input.txt out.txt --sa --iters 30000 --seed 123\n";
}

static int need_int(int &i, int argc, char **argv, const std::string &flag)
{
    if (i + 1 >= argc)
        throw std::runtime_error("Missing value after " + flag);
    return std::stoi(argv[++i]);
}

static double need_double(int &i, int argc, char **argv, const std::string &flag)
{
    if (i + 1 >= argc)
        throw std::runtime_error("Missing value after " + flag);
    return std::stod(argv[++i]);
}

int main(int argc, char **argv)
{
    if (argc < 2)
    {
        usage();
        return 1;
    }

    std::string in_file = argv[1];
    std::string out_file;

    // 位置參數：第二個若不是 flag，視為 out.txt
    int i = 2;
    if (i < argc && !is_flag(argv[i]))
    {
        out_file = argv[i];
        ++i;
    }

    // flags
    bool use_sa = false;
    bool strict = false;
    SAOptions sa_opt; // iters/seed/log_every/T0/Tend

    for (; i < argc; ++i)
    {
        std::string s = argv[i];

        if (s == "--sa")
        {
            use_sa = true;
        }
        else if (s == "--strict")
        {
            strict = true;
        }
        else if (s == "--iters")
        {
            sa_opt.iters = need_int(i, argc, argv, "--iters");
        }
        else if (s == "--seed")
        {
            sa_opt.seed = need_int(i, argc, argv, "--seed");
        }
        else if (s == "--log_every")
        {
            sa_opt.log_every = need_int(i, argc, argv, "--log_every");
        }
        else if (s == "--T0")
        {
            sa_opt.T0 = need_double(i, argc, argv, "--T0");
        }
        else if (s == "--Tend")
        {
            sa_opt.Tend = need_double(i, argc, argv, "--Tend");
        }
        else
        {
            usage();
            throw std::runtime_error("Unknown flag: " + s);
        }
    }

    try
    {
        Problem P = parse_problem(in_file);
        sanity_check_fixed(P, in_file);

        int max_w = 0;
        int max_deg = 0;
        for (auto &e : P.edges)
            max_w = std::max(max_w, e.w);
        for (int u = 0; u < P.n(); ++u)
            max_deg = std::max(max_deg, (int)P.adj[u].size());

        std::cout << "chip: " << P.chip_w << " x " << P.chip_h << "\n";
        std::cout << "modules: " << P.n()
                  << " (soft=" << P.soft_ids.size()
                  << ", fixed=" << P.fixed_ids.size() << ")\n";
        std::cout << "edges(merged): " << P.edges.size()
                  << ", max_edge_w: " << max_w
                  << ", max_degree: " << max_deg << "\n";
        std::cout << "[OK] parse + sanity passed.\n";

        // 沒給 out_file 就到此為止（跟你原本一致）
        if (out_file.empty())
            return 0;

        // placement
        Solution S;
        if (use_sa)
        {
            std::cout << "[RUN] SA placement\n";
            S = place_sa(P, sa_opt);
        }
        else
        {
            std::cout << "[RUN] baseline placement\n";
            S = place_obstacle_aware_baseline(P);
        }

        double hpwl = compute_total_hpwl(P, S);
        write_solution(P, S, out_file, hpwl);
        std::cout << "[OK] wrote output: " << out_file << "\n";
        std::cout << "[INFO] HPWL = " << hpwl << "\n";

        // legality check：預設 warn；--strict 則直接 fail
        if (strict)
        {
            check_solution_or_throw(P, S);
            std::cout << "[OK] legal placement\n";
        }
        else
        {
            try
            {
                check_solution_or_throw(P, S);
                std::cout << "[OK] legal placement\n";
            }
            catch (const std::exception &e)
            {
                std::cerr << "[WARN] placement is NOT legal: " << e.what() << "\n";
            }
        }
    }
    catch (const std::exception &e)
    {
        std::cerr << "[ERROR] " << e.what() << "\n";
        return 2;
    }
    return 0;
}
