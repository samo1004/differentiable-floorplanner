#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <cstdint>
#include <algorithm>

struct Rect {
    int x=0, y=0, w=0, h=0; // left-bottom + size
    int x2() const { return x + w; }
    int y2() const { return y + h; }
};

inline bool overlap_area_positive(const Rect& a, const Rect& b) {
    int ix = std::min(a.x2(), b.x2()) - std::max(a.x, b.x);
    int iy = std::min(a.y2(), b.y2()) - std::max(a.y, b.y);
    return ix > 0 && iy > 0; // 只禁止正面積交集；貼邊 OK
}

enum class ModuleType : uint8_t { Soft, Fixed };

struct Module {
    std::string name;
    ModuleType type = ModuleType::Soft;

    // soft
    int min_area = 0;

    // fixed
    Rect fixed_rect{};
};

struct Edge {
    int u=-1, v=-1;
    int w=0;
};

struct Problem {
    int chip_w=0, chip_h=0;

    std::vector<Module> modules;
    std::vector<int> soft_ids, fixed_ids;
    std::unordered_map<std::string,int> name2id;

    std::vector<Edge> edges; // merged undirected
    std::vector<std::vector<std::pair<int,int>>> adj; // (nbr, weight)

    int n() const { return (int)modules.size(); }
};

inline uint64_t pack_undirected_pair(int a, int b) {
    int u = std::min(a,b), v = std::max(a,b);
    return (uint64_t)(uint32_t)u << 32 | (uint32_t)v;
}
