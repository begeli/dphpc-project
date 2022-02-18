#pragma once
#include "metadata.h"
#include "MultiIndex.h"

namespace ptc {

// Local Data class represents the partial input and output tensors that will be used and produced
// in the tensor contraction.
class LocalData {
 public:
  LocalData() {
    rankIDs = std::vector<int>{-1}; // <0 for an "invalid" ID, as a scalar doesn't actually have any output rank ID
    indexOffsets = std::vector<int>{1};
    localDims = std::vector<int>{1};
  }

  int computeCurrentIndex(MultiIndex&) const;

  LocalData(LocalData&&) noexcept;

  LocalData& operator=(LocalData&&) noexcept;

  LocalData(const LocalData&) = delete;
  LocalData& operator=(const LocalData&) = delete;

  ~LocalData() = default;

  LocalData(data_type* data,
            const std::vector<int>& rankIDs,
            const std::vector<int>& localDims);

  // PROPERTIES
  data_type* data{};
  /// Map the slice's rank to its ID - Ranks need a ID to distinguish
  /// them between ranks of other inputs as different inputs can have different
  /// ranks. The key in the map corresponds to the index in the dims vector.
  std::vector<int> rankIDs;
  /// indexOffsets[i] contains the number of elements we skip when the corresponding iteration variable
  /// is increased by 1.
  std::vector<int> indexOffsets;
  /// Local Dims is the number of dimensions each rank of local input receives
  std::vector<int> localDims;
};

} // namespace ptc
