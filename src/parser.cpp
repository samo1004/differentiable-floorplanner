#include "parser.hpp"
#include <fstream>
#include <stdexcept>

// 會傳進來got是讀到的tag(string)，expected是我們預期的tag(string)，file是檔案名稱(string)
static void expect_tag(const std::string &got, const std::string &expected, const std::string &file)
{
    if (got != expected)
    {
        throw std::runtime_error("ParseError[file=" + file + "]: expected '" + expected + "' but got '" + got + "'");
    }
}

static int add_module(Problem &P, Module m, const std::string &file, const std::string &section, int idx1)
{
    if (P.name2id.count(m.name)) // 先檢查有沒有重複的模組名稱
    {
        throw std::runtime_error("ParseError[file=" + file + "][" + section + " #" + std::to_string(idx1) +
                                 "]: duplicate module name '" + m.name + "'");
    }
    int id = (int)P.modules.size(); // 第一個模組id是0
    P.modules.push_back(std::move(m));
    P.name2id[P.modules[id].name] = id; // name2id是一個 std::unordered_map，key是模組名稱，value是模組id
    return id;
}

Problem parse_problem(const std::string &path)
{
    std::ifstream fin(path);
    if (!fin)
        throw std::runtime_error("ParseError: cannot open file: " + path);

    Problem P;
    std::string tag; // 暫時存讀到的tag

    // CHIP w h
    fin >> tag;
    expect_tag(tag, "CHIP", path);
    fin >> P.chip_w >> P.chip_h;

    // SOFTMODULE n
    fin >> tag;
    expect_tag(tag, "SOFTMODULE", path);
    int n_soft = 0;
    fin >> n_soft; // 讀可變形模組數量
    for (int i = 0; i < n_soft; ++i)
    {
        Module m; // 建立模組物件
        m.type = ModuleType::Soft;
        fin >> m.name >> m.min_area;                                     // 讀模組名稱與最小面積
        int id = add_module(P, std::move(m), path, "SOFTMODULE", i + 1); // 加入模組並取得模組ID
        P.soft_ids.push_back(id);
    }

    // FIXEDMODULE m
    fin >> tag;
    expect_tag(tag, "FIXEDMODULE", path);
    int n_fixed = 0;
    fin >> n_fixed; // 讀固定模組數量
    for (int i = 0; i < n_fixed; ++i)
    {
        Module m; // 建立模組物件
        m.type = ModuleType::Fixed;
        fin >> m.name >> m.fixed_rect.x >> m.fixed_rect.y >> m.fixed_rect.w >> m.fixed_rect.h;
        int id = add_module(P, std::move(m), path, "FIXEDMODULE", i + 1);
        P.fixed_ids.push_back(id);
    }

    // CONNECTION k
    fin >> tag;
    expect_tag(tag, "CONNECTION", path);
    int k = 0;
    fin >> k;

    std::unordered_map<uint64_t, int> merged;
    merged.reserve((size_t)k * 2);

    for (int i = 0; i < k; ++i)
    {
        std::string a, b;
        int w = 0;
        fin >> a >> b >> w;

        auto ita = P.name2id.find(a);
        auto itb = P.name2id.find(b);
        if (ita == P.name2id.end() || itb == P.name2id.end())
        {
            throw std::runtime_error("ParseError[file=" + path + "][CONNECTION #" + std::to_string(i + 1) +
                                     "]: unknown module '" + a + "' or '" + b + "'");
        }
        int u = ita->second, v = itb->second;
        if (u == v)
            continue;
        merged[pack_undirected_pair(u, v)] += w; // case02: merge duplicates
    }

    P.edges.reserve(merged.size());
    P.adj.assign(P.n(), {});
    for (auto &kv : merged)
    {
        uint64_t key = kv.first;
        int u = (int)(key >> 32);
        int v = (int)(key & 0xffffffffu);
        int w = kv.second;
        P.edges.push_back({u, v, w});
        P.adj[u].push_back({v, w});
        P.adj[v].push_back({u, w});
    }

    return P;
}
