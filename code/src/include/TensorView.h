#pragma once

#include <utility>
#include <vector>
#include <numeric>

/// VERY unsafe. No checks whatsoever of valid inputs or accesses.
/// TODO turn this into an MPI derived datatype to send our non-contiguous data
class TensorView {
  float* T;
  const size_t* dimensions;
  size_t outer_stride;
  int rank;

  /// For internal use only
  TensorView(float* T, const size_t* dimensions, size_t outer_stride, int rank) : T{T},
                                                                            dimensions{dimensions},
                                                                            outer_stride{outer_stride},
                                                                            rank{rank} {}

 public:
  /// Initialize a tensorview given contiguous raw data and the desired rank sizes
  TensorView(float* T, const std::vector<size_t>& ranks) : T{T},
                                                        dimensions{ranks.data()},
                                                        outer_stride{std::reduce(ranks.begin() + 1, ranks.end(), 1UL, std::multiplies<>())},
                                                        rank(ranks.size()) {}

  TensorView operator[](int i) {
    return {&(T[i * outer_stride]), &(dimensions[1]), outer_stride / dimensions[1], rank - 1};
  }

  operator float*() {
    return T;
  }
};
