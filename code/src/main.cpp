#include <iostream>
#include <memory>
#include <numeric>
#include <vector>
#include <cmath>
#include <regex>
#include <cstring>
#include "mpi/mpi_utils.h"
#include "include/TensorView.h"
#include "include/ptc.h"

#include "include/MultiIndex.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace std;
using namespace std::string_literals;

using namespace ptc;

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

void testFull() {
  MyMPI m{nullptr, nullptr};
  int rank = m.get_rank();

  std::cout << "[" << rank << "] Starting end-to-end test for MTT-KRP..." << std::endl;
  std::vector<std::vector<float>> inputs{};
  data_type a[3 * 5 * 5] = {0.59653751, 0.50725633, 0.15625563, 0.99372101, 0.31173241,
                            0.69900654, 0.81417494, 0.29421625, 0.51527076, 0.75900901,
                            0.07323442, 0.38214865, 0.75007424, 0.06507908, 0.10286522,
                            0.56323007, 0.73079416, 0.78760573, 0.1451608, 0.75837708,
                            0.45055567, 0.51603294, 0.32444965, 0.72996413, 0.58185089,
                            0.05828005, 0.19650178, 0.53740703, 0.22124199, 0.21336625,
                            0.02921446, 0.45789295, 0.29278434, 0.55033416, 0.35233661,
                            0.14099192, 0.1169395, 0.1277336, 0.91277863, 0.68319358,
                            0.85955414, 0.30811584, 0.91904295, 0.48264387, 0.41257195,
                            0.95077216, 0.69353344, 0.14101123, 0.27376056, 0.63676415,
                            0.07615025, 0.04071383, 0.62544017, 0.70563608, 0.39876665,
                            0.37933203, 0.75311157, 0.34091597, 0.06896424, 0.58267823,
                            0.82476301, 0.74628775, 0.97956889, 0.68750272, 0.2826161,
                            0.11762574, 0.80142085, 0.04905171, 0.72459151, 0.58401467,
                            0.37040275, 0.83391645, 0.38190071, 0.68311293, 0.72778809};
  data_type b[5 * 4] = {0.7754742, 0.54433881, 0.25817609, 0.15536148, 0.13157443,
                        0.7880699, 0.43092533, 0.59176003, 0.08545946, 0.87344421,
                        0.12831613, 0.23888046, 0.93364646, 0.40748787, 0.86787966,
                        0.83683222, 0.68316486, 0.3633883, 0.89190713, 0.90021718};
  data_type c[5 * 4] = {0.30554421, 0.96130472, 0.35720728, 0.88082087, 0.36292857,
                        0.34126651, 0.9106766, 0.74659785, 0.55700836, 0.80049978,
                        0.92867106, 0.42370061, 0.2592759, 0.53941273, 0.16679549,
                        0.54574786, 0.22078221, 0.06921142, 0.49460505, 0.08510545};

  // ijk, kl, jl -> il
  // i = 0, j = 1, k = 2, j = 3
  std::vector<std::vector<int>> inputRankIDs{{0, 1, 2}, {2, 3}, {1, 3}};
  std::vector<int> outputRankIDs{0, 3};
  std::vector<std::vector<int>> inputDims{{3, 5, 5}, {5, 4}, {5, 4}};
  std::vector<int> outputDims{3, 4};
  // Ranks 1, 2 work on first row of output: [1.95179666, 3.90430684, 3.47275307, 3.88317959]
  // Rank 3, 4 work on second row of output: [1.99828928, 2.95809314, 3.42278582, 2.86400505]
  // Ranks 0, 5, 6, 7 work on third row of output: [2.24069111, 4.08175584, 3.86049226, 3.61600952]
  std::vector<Slice> iteration_var_ranges{
      { // rank 0
          {2, 3}, // i
          {0, 2}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 1
          {0, 1}, // i
          {0, 2}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 2
          {0, 1}, // i
          {2, 5}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 3
          {1, 2}, // i
          {0, 3}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 4
          {1, 2}, // i
          {3, 5}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 5
          {2, 3}, // i
          {2, 3}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 6
          {2, 3}, // i
          {3, 4}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
      { // rank 7
          {2, 3}, // i
          {4, 5}, // j
          {0, 5}, // k
          {0, 4}  // l
      },
  };

  std::vector<std::vector<Slice>> inputRanges{
      { // rank 0
          {{2, 3}, {0, 2}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{0, 2}, {0, 4}}     // input 2
      },
      { // rank 1
          {{0, 1}, {0, 2}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{0, 2}, {0, 4}}     // input 2
      },
      { // rank 2
          {{0, 1}, {2, 5}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{2, 5}, {0, 4}}     // input 2
      },
      { // rank 3
          {{1, 2}, {0, 3}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{0, 3}, {0, 4}}     // input 2
      },
      { // rank 4
          {{1, 2}, {3, 5}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{3, 5}, {0, 4}}     // input 2
      },
      { // rank 5
          {{2, 3}, {2, 3}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{2, 3}, {0, 4}}     // input 2
      },
      { // rank 6
          {{2, 3}, {3, 4}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{3, 4}, {0, 4}}     // input 2
      },
      { // rank 7
          {{2, 3}, {4, 5}, {0, 5}}, // input 0
          {{0, 5}, {0, 4}},    // input 1
          {{4, 5}, {0, 4}}     // input 2
      }
  };
  std::vector<Slice> outputRanges{
      { // rank 0
          {2, 3}, {0, 4}
      },
      { // rank 1
          {0, 1}, {0, 4}
      },
      { // rank 2
          {0, 1}, {0, 4}
      },
      { // rank 3
          {1, 2}, {0, 4}
      },
      { // rank 4
          {1, 2}, {0, 4}
      },
      { // rank 5
          {2, 3}, {0, 4}
      },
      { // rank 6
          {2, 3}, {0, 4}
      },
      { // rank 7
          {2, 3}, {0, 4}
      }
  };

  // again the dimensions (of the slices).
  // there might be quite the redundancy between this and input/outputRanges
  std::vector<std::vector<int>> iteration_var_limits{
      {1, 2, 5, 4}, // rank 0
      {1, 2, 5, 4}, // rank 1
      {1, 3, 5, 4}, // rank 2
      {1, 3, 5, 4}, // rank 3
      {1, 2, 5, 4}, // rank 4
      {1, 1, 5, 4}, // rank 5
      {1, 1, 5, 4}, // rank 6
      {1, 1, 5, 4}, // rank 7
  };

  // Only rank 0 starts knowing the tensors. It has to distribute them to the other ranks first.
  data_type* rt_0 = rank != 0 ? nullptr : a;
  data_type* rt_1 = rank != 0 ? nullptr : b;
  data_type* rt_2 = rank != 0 ? nullptr : c;

  std::vector<data_type*> ssv(3); // 3 inputs
  for (int i = 0; i < ssv.size(); ++i) {
    std::vector<int> subsizes{};
    subsizes.reserve(inputRanges[rank][i].size());
    std::transform(inputRanges[rank][i].begin(),
                   inputRanges[rank][i].end(),
                   std::back_inserter(subsizes),
                   [](std::pair<size_t, size_t> p) {
                     return p.second - p.first;
                   });
    int slice_size = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
    ssv[i] = static_cast<data_type*>(calloc(slice_size, sizeof(data_type)));
  }

  std::vector<DistributionData> distribution{
      {rt_0, ssv[0]}, // input 0
      {rt_1, ssv[1]}, // input 1
      {rt_2, ssv[2]}  // input 2
  };

  std::vector<int> subsizes{};
  subsizes.reserve(outputRanges[rank].size());
  std::transform(outputRanges[rank].begin(),
                 outputRanges[rank].end(),
                 std::back_inserter(subsizes),
                 [](std::pair<size_t, size_t> p) {
                   return p.second - p.first;
                 });
  int reduce_local_size = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
  auto* reduce_local = static_cast<data_type*>(calloc(reduce_local_size, sizeof(data_type)));

  int reduce_final_size = std::reduce(outputDims.begin(), outputDims.end(), 1, std::multiplies<>());
  auto* reduce_final = rank != 0 ? nullptr : static_cast<data_type*>(calloc(reduce_final_size, sizeof(data_type)));

  ReductionData reduction{reduce_final, reduce_local};
  int index_count = 4;

  ContractionData tc_metadata
      {inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges, outputRanges, iteration_var_limits,
       distribution, reduction,
       index_count};

  LocalData output = contractTensors<true>(tc_metadata);

  if (rank == 0) {
    std::cout << "Contraction result:\n";
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 4; ++j) {
        std::cout << tc_metadata.reduction.root_reduced[i * 4 + j] << " ";
      }
      std::cout << "\n";
    }
    std::cout << std::endl;
  }

  // Free the previously allocated memory.
  for (auto ptr: ssv) free(ptr);
  free(reduce_local);
  if (rank == 0) free(reduce_final);

// expected output:
// array([[1.95179666, 3.90430684, 3.47275307, 3.88317959],
//       [1.99828928, 2.95809314, 3.42278582, 2.86400505],
//       [2.24069111, 4.08175584, 3.86049226, 3.61600952]])
}

// TODO segfaults with do_distribute false
std::vector<data_type> do_contraction(bool do_distribute,
                                      int index_count,
                                      const std::vector<std::vector<int>>& inputRankIDs,
                                      const std::vector<int>& outputRankIDs,
                                      const std::vector<std::vector<int>>& inputDims,
                                      const std::vector<int>& outputDims,
                                      const std::vector<std::vector<std::vector<std::pair<size_t, size_t>>>>& inputRanges,
                                      const std::vector<std::vector<std::pair<size_t, size_t>>>& outputRanges,
                                      const std::vector<std::vector<int>>& iteration_var_limits,
                                      std::vector<std::vector<data_type>>& data) {
  MyMPI m{nullptr, nullptr};
  int rank = m.get_rank();

  std::cout << "[" << rank << "] Starting end-to-end contraction..." << std::endl;

  std::vector<DistributionData> distribution;
  for (int i = 0; i < inputRankIDs.size(); ++i) {
    std::cout << "[" << rank << "] Adding input " << i << "..." << std::endl;
    std::vector<int> subsizes{};
    subsizes.reserve(inputRanges[rank][i].size());
    std::transform(inputRanges[rank][i].begin(),
                   inputRanges[rank][i].end(),
                   std::back_inserter(subsizes),
                   [](std::pair<size_t, size_t> p) {
                     return p.second - p.first;
                   });
    int slice_size = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
    distribution.emplace_back(rank == 0 ? data[i].data() : nullptr,
                              do_distribute? static_cast<data_type*>(calloc(slice_size, sizeof(data_type))) : data[i].data());
  }

  std::vector<int> subsizes{};
  subsizes.reserve(outputRanges[rank].size());
  std::transform(outputRanges[rank].begin(),
                 outputRanges[rank].end(),
                 std::back_inserter(subsizes),
                 [](std::pair<size_t, size_t> p) {
                   return p.second - p.first;
                 });
  int reduce_local_size = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
  auto* reduce_local = static_cast<data_type*>(calloc(reduce_local_size, sizeof(data_type)));

  int reduce_final_size = std::reduce(outputDims.begin(), outputDims.end(), 1, std::multiplies<>());
  //auto* reduce_final = rank != 0 ? nullptr : static_cast<data_type*>(calloc(reduce_final_size, sizeof(data_type)));
  std::vector<data_type> reduce_final(rank == 0 ? reduce_final_size : 1, 0);

  ReductionData reduction{reduce_final.data(), reduce_local};

  ContractionData tc_metadata
      {inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges, outputRanges, iteration_var_limits,
       distribution, reduction,
       index_count};

  LocalData output = do_distribute? contractTensors<true>(tc_metadata) : contractTensors<false>(tc_metadata);

  if (rank == 0) {
    std::cout << "(A subset of the) contraction result:\n";
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 4; ++j) {
        std::cout << tc_metadata.reduction.root_reduced[i * 4 + j] << " ";
      }
      std::cout << "\n";
    }
    std::cout << std::endl;
  }

  // Free the previously allocated memory.
  if (do_distribute) for (auto ptr: distribution) free(ptr.local_contig);
  free(reduce_local);
  return reduce_final;
}

int main() {
  testFull();
  return 0;
}

void some_func(const std::vector<std::vector<int>>& inputRankIDs,
               const std::vector<int>& outputRankIDs,
               const std::vector<std::vector<int>>& inputDims,
               const std::vector<int>& outputDims,
               const std::vector<std::vector<std::vector<std::pair<int, int>>>>& inputRanges,
               const std::vector<std::vector<std::vector<std::pair<int, int>>>>& outputRanges,
               const std::vector<std::vector<int>>& iteration_var_limits,
               const std::vector<std::vector<float>>& data = vector<vector<float>>()) {
  for (int i = 0; i < inputRankIDs.size(); i++) {
    for (int j = 0; j < inputRankIDs[i].size(); j++) {
      std::cout << inputRankIDs[i][j] << ' ';
    }
    std::cout << std::endl;
  }
  std::cout << std::endl;
  for (int i = 0; i < outputRankIDs.size(); i++) {
    std::cout << outputRankIDs[i] << ' ';
  }
  std::cout << std::endl;
  std::cout << std::endl;
  for (int i = 0; i < inputDims.size(); i++) {
    for (int j = 0; j < inputDims[i].size(); j++) {
      std::cout << inputDims[i][j] << ' ';
    }
    std::cout << std::endl;
  }
  std::cout << std::endl;
  for (int i = 0; i < outputDims.size(); i++) {
    std::cout << outputDims[i] << ' ';
  }
  std::cout << std::endl;
  std::cout << std::endl;
  for (int i = 0; i < inputRanges.size(); i++) {
    for (int j = 0; j < inputRanges[i].size(); j++) {
      for (int k = 0; k < inputRanges[i][j].size(); k++) {
        std::cout << inputRanges[i][j][k].first << ' ' << inputRanges[i][j][k].second;
        std::cout << std::endl;
      }
    }
  }
  for (int i = 0; i < outputRanges.size(); i++) {
    for (int j = 0; j < outputRanges[i].size(); j++) {
      for (int k = 0; k < outputRanges[i][j].size(); k++) {
        std::cout << outputRanges[i][j][k].first << ' ' << outputRanges[i][j][k].second;
        std::cout << std::endl;
      }
    }
  }
  for (int i = 0; i < iteration_var_limits.size(); i++) {
    for (int j = 0; j < iteration_var_limits[i].size(); j++) {
      std::cout << iteration_var_limits[i][j] << ' ';
    }
    std::cout << std::endl;
  }
}

namespace py = pybind11;

PYBIND11_MODULE(pybind_gjk, m) {
//  m.def("print_slices", &print_slices, "Print the slices.");
  m.def("main", &main, "Start the main program");
  m.def("some_func", &some_func, "Start the thing");
  m.def("do_contraction", &do_contraction, "Do the contraction.");
}
