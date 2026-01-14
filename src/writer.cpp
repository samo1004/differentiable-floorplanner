#include "writer.hpp"
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <vector>

static std::vector<std::pair<int, int>> rectangle_corners_clockwise(const Rect &r)
{
    return {
        {r.x, r.y},       // bottom-left
        {r.x, r.y2()},    // top-left
        {r.x2(), r.y2()}, // top-right
        {r.x2(), r.y},    // bottom-right
    };
}

void write_solution(const Problem &P, const Solution &S,
                    const std::string &out_path, double hpwl)
{
    std::ofstream fout(out_path);
    if (!fout)
        throw std::runtime_error("WriteError: cannot open output file: " + out_path);

    fout << std::fixed << std::setprecision(1);
    fout << "HPWL " << hpwl << "\n";
    fout << "SOFTMODULE " << P.soft_ids.size() << "\n";

    for (int sid : P.soft_ids)
    {
        const auto &m = P.modules[sid];
        const Rect &r = S.rect(sid);
        if (r.w <= 0 || r.h <= 0)
        {
            throw std::runtime_error("WriteError: soft module has non-positive w/h: " + m.name);
        }

        auto corners = rectangle_corners_clockwise(r);
        fout << m.name << " " << corners.size() << "\n";
        for (auto [x, y] : corners)
        {
            if (x < 0 || y < 0)
            {
                throw std::runtime_error("WriteError: negative coordinate for module: " + m.name);
            }
            fout << x << " " << y << "\n";
        }
    }
}
