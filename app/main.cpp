#include <iostream>
#include <algorithm>
#include "parser.hpp"
#include "sanity.hpp"

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "Usage: placer <case-input.txt>\n";
        return 1;
    }
    std::string file = argv[1];

    try
    {
        Problem P = parse_problem(file);
        sanity_check_fixed(P, file);

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

        // print all parsed modules
        for (int i = 0; i < P.n(); ++i)
        {
            const Module &m = P.modules[i];
            std::cout << "Module " << i << ": " << m.name
                      << ", type=" << (m.type == ModuleType::Soft ? "Soft" : "Fixed");
            if (m.type == ModuleType::Soft)
            {
                std::cout << ", min_area=" << m.min_area << "\n";
            }
            else
            {
                std::cout << ", fixed_rect=("
                          << m.fixed_rect.x << "," << m.fixed_rect.y
                          << "," << m.fixed_rect.w << "," << m.fixed_rect.h << ")\n";
            }
        }

        // print all parsed edges
        for (const auto &e : P.edges)
        {
            std::cout << "Edge: (" << e.u << ", " << e.v << "), weight=" << e.w << "\n";
        }
    }
    catch (const std::exception &e)
    {
        std::cerr << "[ERROR] " << e.what() << "\n";
        return 2;
    }

    return 0;
}
