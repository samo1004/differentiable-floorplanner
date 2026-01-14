#include <iostream>
#include <algorithm>

#include "parser.hpp"
#include "sanity.hpp"
#include "baseline.hpp"
#include "hpwl.hpp"
#include "writer.hpp"
#include "checker.hpp"

int main(int argc, char **argv)
{
    if (argc != 2 && argc != 3)
    {
        std::cerr << "Usage: placer <case-input.txt> [out.txt]\n";
        return 1;
    }
    std::string in_file = argv[1];
    std::string out_file = (argc == 3 ? argv[2] : "");

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

        if (!out_file.empty())
        {
            Solution S = place_row_packing_baseline(P);
            double hpwl = compute_total_hpwl(P, S);
            write_solution(P, S, out_file, hpwl);
            std::cout << "[OK] wrote output: " << out_file << "\n";

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
