#include "LocalData.h"

namespace ptc{
LocalData::LocalData(LocalData&& o) noexcept: rankIDs{std::move(o.rankIDs)},
                                                     indexOffsets{std::move(o.indexOffsets)},
                                                     localDims{std::move(o.localDims)} {
  data = o.data;
  o.data = nullptr;
}

LocalData& LocalData::operator=(LocalData&& o) noexcept {
  assert(this != &o);
  rankIDs = std::move(o.rankIDs);
  indexOffsets = std::move(o.indexOffsets);
  localDims = std::move(o.localDims);

  data = o.data;
  o.data = nullptr;

  return *this;
}

/**
 * Based on the iteration variables a LocalData object has and the current values of these
 * iteration variables in the Multi-Index object compute the index to be accessed to receive or
 * store data.
 * @param multiIndex: MultiIndex object which holds the iteration space state.
 * @return index: Index value to be accessed.
 * */
int LocalData::computeCurrentIndex(MultiIndex& multiIndex) const {
  int index = 0;
  for (size_t pos = 0; pos < rankIDs.size(); pos++) {
    int rankID = rankIDs[pos];
    index += multiIndex.getIndex(rankID) * indexOffsets[pos];
  }

  return index;
}

LocalData::LocalData(data_type* data,
                            const std::vector<int>& rankIDs,
                            const std::vector<int>& localDims) : data{data},
                                                                 rankIDs{rankIDs},
                                                                 localDims{localDims} {
  indexOffsets = std::vector<int>(rankIDs.size());
  indexOffsets[indexOffsets.size() - 1] = 1;
  for (int i = indexOffsets.size() - 2; i >= 0; i--) {
    indexOffsets[i] = indexOffsets[i + 1] * localDims[i + 1];
  }
}
} // namespace ptc
