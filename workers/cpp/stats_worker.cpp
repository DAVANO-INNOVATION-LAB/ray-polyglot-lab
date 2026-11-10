#include <charconv>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static std::int64_t number(const std::string &token) {
    const auto offset = (!token.empty() && token[0] == '-') ? 1U : 0U;
    if (token.size() <= offset || (token.size() > offset + 1 && token[offset] == '0')) {
        throw std::invalid_argument("number");
    }
    for (std::size_t i = offset; i < token.size(); ++i) {
        if (token[i] < '0' || token[i] > '9') throw std::invalid_argument("number");
    }
    std::int64_t value = 0;
    const auto parsed = std::from_chars(token.data(), token.data() + token.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != token.data() + token.size()) {
        throw std::invalid_argument("number");
    }
    return value;
}

int main() {
    try {
        std::string input;
        char c = 0;
        while (std::cin.get(c)) {
            auto byte = static_cast<unsigned char>(c);
            if (input.size() == 65536 || byte > 127 ||
                (byte < 32 && c != '\t' && c != '\n' && c != '\r')) {
                throw std::invalid_argument("request");
            }
            input.push_back(c);
        }
        std::istringstream stream(input);
        std::vector<std::string> tokens;
        std::string token;
        while (stream >> token) tokens.push_back(token);
        if (tokens.size() < 2 || tokens[0] != "RAYPOLY1") {
            throw std::invalid_argument("request");
        }
        auto n = number(tokens[1]);
        if (n < 0 || n > 4096 || tokens.size() != static_cast<std::size_t>(n + 2)) {
            throw std::invalid_argument("count");
        }
        std::int64_t sum = 0;
        std::int64_t squares = 0;
        for (std::size_t i = 2; i < tokens.size(); ++i) {
            auto value = number(tokens[i]);
            if (value < -1000000 || value > 1000000) throw std::invalid_argument("value");
            sum += value;
            squares += value * value;
        }
        std::cout << "{\"protocol\":\"RAYPOLY1\",\"language\":\"cpp\",\"count\":" << n
                  << ",\"sum\":" << sum << ",\"sum_squares\":" << squares << "}\n";
        return 0;
    } catch (const std::exception &) {
        std::cerr << "invalid request\n";
        return 2;
    }
}
