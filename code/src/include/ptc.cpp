#include <numeric>
#include "ptc.h"



namespace {
// Printing a vector automatically.
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

// TODO Try a finding a way without hashing a vector...
struct hash_pair final {
  template<class TFirst, class TSecond>
  size_t operator()(const std::pair<TFirst, TSecond>& p) const noexcept {
    uintmax_t hash = std::hash<TFirst>{}(p.first);
    hash <<= sizeof(uintmax_t) * 4;
    hash ^= std::hash<TSecond>{}(p.second);
    return std::hash<uintmax_t>{}(hash);
  }
};

//using boost::hash_combine
template<class T>
inline void hash_combine(std::size_t& seed, T const& v) {
  seed ^= std::hash<T>()(v) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

inline size_t key(size_t i, size_t j) { return (i << 32) | j; }

inline void hash_combine(std::size_t& seed, std::pair<size_t, size_t> const& p) {
  seed ^= key(p.first, p.second) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}
} // namespace

// Still hashing vector stuff. We "hack" the vector hash function into std namespace.
namespace std {
template<typename T>
struct hash<vector<T>> {
  typedef vector<T> argument_type;
  typedef std::size_t result_type;
  result_type operator()(argument_type const& in) const {
    size_t size = in.size();
    size_t seed = 0;
    for (size_t i = 0; i < size; i++)
      //Combine the hash of the current vector with the hashes of the previous ones
      hash_combine(seed, in[i]);
    return seed;
  }
};
} // namespace std


namespace ptc {
/**
 * Compute the multiplication of tensor elements based on the current state of the iteration space.
 * */
data_type multiplyIndexElements(const std::vector<LocalData>& inputs, MultiIndex& multi_index) {
  data_type res = 1.0f;

  // Update the multiplication result
  for (auto& input: inputs) {
    int index = input.computeCurrentIndex(multi_index);

    res *= input.data[index];
  }

  return res;
}

/**
 * @return scalar: A Local Data object contracted to a single value
 * */
LocalData reduceToScalar(const ContractionData& data, const std::vector<LocalData>& inputs, MultiIndex& multi_index) {
  data_type scalar = 0.0f;

  while (multi_index.canIterate()) {
    scalar += multiplyIndexElements(inputs, multi_index);

    multi_index.iterate();
  }

  LocalData o{data.reduction.local_result, data.outputRankIDs, {1}};
  o.data[0] = scalar;

  return o; // copy elision
}

/**
 * @return outputPartition: The partial result of the tensor contraction.
 * */
LocalData localContraction(const ContractionData& data, const MyMPI_Comm& comm) {
  int comm_rank = comm.get_comm_rank();

  MultiIndex multi_index{data};
  std::vector<LocalData> localInputs{};

  // Compute the local input Dims
  std::vector<std::vector<int>> inputDimVec(data.inputRanges[comm_rank].size());
  int i = 0;
  for (const auto& inputRange: data.inputRanges[comm_rank]) {
    std::transform(inputRange.begin(),
                   inputRange.end(),
                   std::back_inserter(inputDimVec[i]),
                   [](const std::pair<size_t, size_t>& p) {
                     return static_cast<int>(p.second - p.first);
                   });
    ++i;
  }

  localInputs.reserve(data.inputRankIDs.size());
  for (int x = 0; x < data.inputRankIDs.size(); ++x) {
    localInputs.emplace_back(data.distribution[x].local_contig, data.inputRankIDs[x], inputDimVec[x]);
  }

  // Reduce output to a scalar value
  if (data.outputRankIDs.empty()) {
    return reduceToScalar(data, localInputs, multi_index);
  }

  // Create the output object
  std::vector<int> outputLocalDims;
  for (auto outputRankID: data.outputRankIDs) {
    outputLocalDims.push_back(data.iteration_var_limits[comm_rank][outputRankID]);
  }
  LocalData outputPartition{data.reduction.local_result, data.outputRankIDs, outputLocalDims};

  // Compute the tensor contraction
  while (multi_index.canIterate()) {
    int outputIndex = outputPartition.computeCurrentIndex(multi_index);
    outputPartition.data[outputIndex] += multiplyIndexElements(localInputs, multi_index);

    multi_index.iterate();
  }

  return outputPartition; // copy elision
}

void distributeSingleInput(size_t input_idx, const ContractionData& data, const MyMPI_Comm& comm) {
  std::cout << "["<< comm.get_comm_rank() << "] Starting distribution of " << input_idx << "..." << std::endl;

  std::unordered_map<Slice, std::vector<int>> group_map{};

  for (int i = 0; i < data.inputRanges.size(); ++i) {
    const auto& range = data.inputRanges[i][input_idx];
    auto& ranklist = group_map[range];
    // 0 is the broadcaster - and as such will be part of any group
    if (ranklist.empty()) ranklist.push_back(0);
    // The i is the rank of the processor with the current slice
    if (i > 0) ranklist.push_back(i);
  }

  // Actual broadcasting
  for (const auto& entry: group_map) {
    const Slice& range = entry.first;

    MyMPI_Comm bcomm{entry.second, comm};
    if (!bcomm.contains_caller()) continue;

    // Deal with subsizes
    std::vector<int> subsizes{};
    subsizes.reserve(range.size());
    std::transform(range.begin(), range.end(), std::back_inserter(subsizes), [](std::pair<size_t, size_t> p) {
      return p.second - p.first;
    });

    // Deal with start indices
    std::vector<int> starts{};
    starts.reserve(range.size());
    std::transform(range.begin(), range.end(), std::back_inserter(starts), [](std::pair<size_t, size_t> p) {
      return p.first;
    });

    // Create the datatype
    MPI_Datatype subtensor;
    MPI_Type_create_subarray(data.inputDims[input_idx].size(),
                             data.inputDims[input_idx].data(),
                             subsizes.data(),
                             starts.data(),
                             MPI_ORDER_C,
                             mpi_data_type,
                             &subtensor);
    MPI_Type_commit(&subtensor);

    // The actual broadcast: non-contiguous subarray from 0 -> received as contiguous data
    int rank = bcomm.get_comm_rank();
    int count = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
    std::cout << "["<< rank << "] Before bcast..." << std::endl;
#ifdef TC_COMM_COUNTERS
    tc_bytes_sent_bcast += sizeof(data_type) * count;
#endif

    MPI_Bcast(rank == 0 ? data.distribution[input_idx].root_tensor : data.distribution[input_idx].local_contig,
              rank == 0 ? 1 : count,
              rank == 0 ? subtensor : mpi_data_type,
              0,
              bcomm);
    std::cout << "["<< rank << "] After bcast..." << std::endl;

    // rank-local send of root send to get data from *root_tensor -> into *local_contig tensor
    if (rank == 0 && range == data.inputRanges[0][input_idx]) {
      MPI_Sendrecv(data.distribution[input_idx].root_tensor,
                   1,
                   subtensor,
                   0,
                   0,
                   data.distribution[input_idx].local_contig,
                   count,
                   mpi_data_type,
                   0,
                   0,
                   MPI_COMM_SELF,
                   MPI_STATUS_IGNORE);
    }
  }
}

void distribute(const ContractionData& data, const MyMPI_Comm& comm) {
  for (size_t i = 0; i < data.inputDims.size(); ++i)
    distributeSingleInput(i, data, comm);
}

void reduce(const ContractionData& data, const MyMPI_Comm& comm) {
  std::unordered_map<Slice, std::vector<int>> group_map{};
  for (int i = 0; i < data.outputRanges.size(); ++i) {
    const auto& range = data.outputRanges[i];
    auto& ranklist = group_map[range];

    // Rank 0 is part of any reduction group (but contributes zeroes for the outputs it didn't locally compute).
    // Remove for time, and communication (as it adds extra comm)
        if (ranklist.empty()) ranklist.push_back(0);

    // The i is the rank of the processor with the current slice
    if (i > 0) ranklist.push_back(i);
  }

  // Actual reduction
  for (const auto& entry: group_map) {
    const Slice& range = entry.first;
    MyMPI_Comm bcomm{entry.second, comm};

    if (!bcomm.contains_caller()) continue; // only reduce on the relevant processors
    int rank = bcomm.get_comm_rank();

    // Deal with subsizes
    std::vector<int> subsizes{};
    subsizes.reserve(range.size());
    std::transform(range.begin(), range.end(), std::back_inserter(subsizes), [](std::pair<size_t, size_t> p) {
      return p.second - p.first;
    });

    // Deal with start indices
    std::vector<int> starts{};
    starts.reserve(range.size());
    std::transform(range.begin(), range.end(), std::back_inserter(starts), [](std::pair<size_t, size_t> p) {
      return p.first;
    });

    // Create the datatype
    MPI_Datatype subtensor;
    MPI_Type_create_subarray(data.outputDims.size(),
                             data.outputDims.data(),
                             subsizes.data(),
                             starts.data(),
                             MPI_ORDER_C,
                             mpi_data_type,
                             &subtensor);
    MPI_Type_commit(&subtensor);
    int count = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());

    bool root_slice = range == data.outputRanges[0];
    // Allocate extra buffer for zeroes for rank-0 processor (who isn't part of this slice)
    data_type* zeroes = root_slice ? nullptr : static_cast<data_type*>(calloc(count, sizeof(data_type)));

#ifdef TC_COMM_COUNTERS
    tc_bytes_sent_reduce += sizeof(data_type) * count;
#endif

    MPI_Reduce(rank == 0 ? MPI_IN_PLACE : data.reduction.local_result,
               root_slice ? data.reduction.local_result : zeroes,
               count,
               mpi_data_type,
               MPI_SUM,
               0,
               bcomm);

    // rank-local send of root send to get data from *local_result -> into *root_reduced tensor
    if (rank == 0) {
      MPI_Sendrecv(root_slice ? data.reduction.local_result : zeroes,
                   count,
                   mpi_data_type,
                   0,
                   0,
                   data.reduction.root_reduced,
                   1,
                   subtensor,
                   0,
                   0,
                   MPI_COMM_SELF,
                   MPI_STATUS_IGNORE);

    }
    if (!root_slice) free(zeroes);
  }
}

//template <bool doDistribution>
//LocalData contractTensors(const ContractionData& data,
//                          const MyMPI_Comm& comm) {
//  if constexpr (doDistribution) distribute(data, comm);
//  std::cout << "["<< comm.get_comm_rank() << "] Distributino done..." << std::endl;
//  LocalData output = localContraction(data, comm);
//  std::cout << "["<< comm.get_comm_rank() << "] Local contraction done..." << std::endl;
//  reduce(data, comm);
//  std::cout << "["<< comm.get_comm_rank() << "] Reduce done..." << std::endl;
//
//  return output; // copy elision
//}
} // namespace ptc
