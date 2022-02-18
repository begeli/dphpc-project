#include <cassert>
#include "MultiIndex.h"

namespace ptc {
MultiIndex::MultiIndex() = default;

MultiIndex::MultiIndex(MultiIndex&& other) = default;

MultiIndex& MultiIndex::operator=(MultiIndex&& other) = default;

namespace {
template<typename T>
std::ostream& operator<<(std::ostream& out, const std::pair<T, T>& v) {
  out << "(" << v.first << "," << v.second << ")";
  return out;
}

template<typename T>
std::ostream& operator<<(std::ostream& out, const std::vector<T>& v) {
  if (!v.empty()) {
    out << '[';
    for (const auto& tv: v) out << tv << ", ";
    out << "\b\b]"; // use two ANSI backspace characters '\b' to overwrite final ", "
  }
  return out;
}
}

MultiIndex::MultiIndex(const ContractionData& tc_metadata, const MyMPI_Comm& comm) {
  int comm_rank = comm.get_comm_rank();

  index_count = tc_metadata.index_count; // NOLINT (size_t -> int warning)
  indices = std::vector<int>(index_count, 0);
  limits = tc_metadata.iteration_var_limits[comm_rank];
}

MultiIndex::~MultiIndex() = default;

// Set the current indices to 0
void MultiIndex::restart() {
//  memset(indices, 0, index_count * sizeof(int));
  std::fill(indices.begin(), indices.end(), 0);
}

/**
 * Update the iteration variables with respect to their limits
 * Use it at the end of a while loop - check if we can still iterate with canIterate function.
 * Example use:
 * while (canIterate()) {
 *  do stuff...
 *  iterate();
 * }
 * */
void MultiIndex::iterate() {
  int index_index = index_count - 1;

  while (index_index >= 0) {
    indices[index_index]++;

    // If the current iteration variable is not greater than its limit,
    // there is no need to update the other iteration variables
    if (indices[index_index] < limits[index_index]) {
      break;
    }

    // Index overflowed, set it to 0.
    if(index_index > 0) indices[index_index] = 0;
    index_index--;
  }
}

// Determine if the iterations can be incremented
bool MultiIndex::canIterate() {
  return indices[0] < limits[0];
}

// Get the current value of a specific iteration variable using its ID.
int MultiIndex::getIndex(int indexID) {
  return indices[indexID];
}
} // namespace ptc
