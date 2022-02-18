#pragma once
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <string>
#include "mpi.h"

//#define DOUBLE
//
//// Depending on our needs we can change the data type here.
//// Data type is the type of the values in the tensors and matrices.
//#ifdef DOUBLE
//    typedef double data_type;
//#else
//    typedef float data_type;
//#endif

// Has to be of type float, as we distribute using hardcoded MPI_FLOAT for now


/**
 * Index range is the dimensions of a rank a partition
 * will receive for a particular data matrix/tensor
 * */
using index_range = std::pair<int, int>;

namespace ptc {
using data_type = float;
const MPI_Datatype mpi_data_type = MPI_FLOAT;

// Non-owning
class DistributionData {
 public:
  //SlicedTensor root_si;
  data_type* root_tensor;
  data_type* local_contig;

  DistributionData(data_type* root_tensor, data_type* local_contig)
      : root_tensor{root_tensor}, local_contig{local_contig} {}

  DistributionData(const DistributionData&) = default;
  DistributionData& operator=(const DistributionData&) = default;

  DistributionData(DistributionData&&) = default;
  DistributionData& operator=(DistributionData&&) = default;

  ~DistributionData() = default;
};

// Non-owning
class ReductionData {
 public:
  //SlicedTensor si;
  data_type* root_reduced;
  data_type* local_result;

  ReductionData(data_type* root_reduced, data_type* local_result)
      : root_reduced{root_reduced}, local_result{local_result} {}

  ReductionData(const ReductionData&) = default;
  ReductionData& operator=(const ReductionData&) = default;

  ReductionData(ReductionData&&) = default;
  ReductionData& operator=(ReductionData&&) = default;

  ~ReductionData() = default;
};

// TODO: Very similar to the slice definition in the common.h file
//  The only difference is the data structure used.
//  In the common.h file we use a map because the specific
//  index ranges of iteration variables matter.
//  With a vector we lose that information.
//  We have to decide which sort of representation to use without breaking the code. ~ Berke
using Slice = std::vector<std::pair<size_t, size_t>>;

struct ContractionData {
  /// Among the (tensor mode)-rank, which ones correspond to this tensor?
  /// inputRankIDs[i] = the rank id's for [input tensor i]
  std::vector<std::vector<int>> inputRankIDs;
  /// the rank id's for the output tensor
  std::vector<int> outputRankIDs;
  /// Dimensions of input tensors, dims[i] = data for [input tensor i]
  /// cd[j] = dimension along (tensor mode)-rank j
  std::vector<std::vector<int>> inputDims;
  /// Dimensions of the output tensor, analogous to the input tensor dimensions
  std::vector<int> outputDims;
  /// ranges[i] = sv the range over data assigned to processor with ID i.
  /// sv[j] = the range over the data of input j
  std::vector<std::vector<Slice>> inputRanges;
  /// analogous to inputRanges but only one output ofc
  std::vector<Slice> outputRanges;
  /// outputRanges[i] = the limits over output data assigned to processor with ID i
  /// [i][j] = limit along tensormode(s) j of proc i
  std::vector<std::vector<int>> iteration_var_limits;
  /// distribution[i] = distribution data for input i
  std::vector<DistributionData> distribution;
  /// the reduction data for the output tensor
  ReductionData reduction;
  /// A set of combination of all ranks from all data tensors/matrices, the key
  /// represents the order one should access the iteration elements in a loop.
  /// (i.e. 0 is the outermost loop iteration variable and size() - 1 is the innermost loop iteration variable)
  int index_count;
};

///**
// * Slice is the index ranges across all ranks of an data/output matrix/tensor
// * */
//using slice = std::unordered_map<int, index_range>;

///**
// * Input slices are the list of all data partitions a node
// * will receive to perform tensor contraction
// * */
//using input_slices = std::vector<slice>;

/**
 * This structure holds metadata about tensor contraction
 * @param iteration_variables: A set of combination of all ranks from all data tensors/matrices, the key
 * represents the order one should access the iteration elements in a loop.
 * (i.e. 0 is the outermost loop iteration variable and size() - 1 is the innermost loop iteration
 * variable)
 * @param outputRankIDs: An ordered vector which holds the ranks the output has.
 * "Order" refers to the index access order in a multi-dimensional array.
 * @param iteration_var_ranges: contains the range [lower, upper) for iteration variable "i" with ID x
 * where x is an unsigned integer
 * */
//struct ContractionData {
////  std::unordered_map<int, int> iteration_variable_ids;
//  std::vector<int> outputRankIDs;
//  Slice iteration_var_ranges;
//};

} // namespace ptc
