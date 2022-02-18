#pragma once

#include <unordered_map>
#include <string>
#include <cstring>
#include "metadata.h"
#include "../mpi/mpi_utils.h"

#include <iostream>

namespace ptc {
/**
 * Main purpose of this class is to facilitate iterating over arbitrarily ranked inputs
 * */
class MultiIndex {
  int index_count;

  // Keys in the map are the order of the iteration variables
  // and the values are the IDs of the iteration variables
  //std::unordered_map<int, int> iteration_order;

  // The keys and values of the iteration_order map are
  // reversed for easy access to the position of a specific iteration variable
  //std::unordered_map<int, int> r_iteration_order;

  // limits represents the final index value indices can attain
  // So, the invariant is indices[i] <= limits[i]
  //int* limits;
  //int* indices;
  std::vector<int> limits;
  std::vector<int> indices;

 public:
  MultiIndex();
  MultiIndex(const ContractionData&, const MyMPI_Comm& comm = MPI_COMM_WORLD);

  MultiIndex(MultiIndex&&);
  MultiIndex& operator=(MultiIndex&&);

  // Copy constructors and assignment deleted
  MultiIndex(const MultiIndex&) = default;
  MultiIndex& operator=(const MultiIndex&) = default;

  ~MultiIndex();

  void restart();
  void iterate();
  bool canIterate();
  int getIndex(int);
};
} // namespace ptc
