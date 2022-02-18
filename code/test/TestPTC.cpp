#include <gtest/gtest.h>
#include <cmath>
#include <string>
#include <numeric>
#include "../src/include/LocalData.h"
#include "../src/include/ptc.h"

//#define MEASURE

#define bench(left, right) \
auto cycles = test::rdtsc_bvh( &do_intersect_bvh, (left), (right)); \
std::cout << cycles << " cycles" << std::endl

#define bench_vec(left, right) \
auto cycles = test::rdtsc_bvh( &do_intersect_bvh_vec, (left), (right)); \
std::cout << cycles << " cycles" << std::endl

#define BENCH_BVH

#ifdef NDEBUG
#define BVH_TEST_VEC
#define BVH_TEST_F16C
#define BVH_TEST_THICC
#endif
//#define CALIBRATE

//#define BVH_TEST_VERBOSE

/**
 * Test BVH implementation
 *
 * Also includes cycle count measurements
 *
 * Additionally, this group of tests shall help to verify that our
 * conversion from .obj to TriMesh works as expected and as intended.
 *
 * The tests in this file created by us by exporting objects from Blender 3D
 */

namespace test {

namespace {
int result = -1; // global so that function calls are not optimized away.

#include <cstdint>
/* ==================== GNU C and possibly other UNIX compilers ===================== */
#if !defined(WIN32) || defined(__GNUC__)

#if defined(__GNUC__) || defined(__linux__)
#define VOLATILE __volatile__
#define ASM __asm__
#else
/* if we're neither compiling with gcc or under linux, we can hope
         * the following lines work, they probably won't */
#define ASM asm
#define VOLATILE
#endif

#define myInt64 unsigned long long
#define INT32 unsigned int

/* ======================== WIN32 ======================= */
#else

#define myInt64 signed __int64
#define INT32 unsigned __int32

#endif

/* This is the RDTSC timer.
 * RDTSC is an instruction on several Intel and compatible CPUs that Reads the
 * Time Stamp Counter. The Intel manuals contain more information.
 */


#define COUNTER_LO(a) ((a).int32.lo)
#define COUNTER_HI(a) ((a).int32.hi)
#define COUNTER_VAL(a) ((a).int64)

#define COUNTER(a) \
    ((unsigned long long)COUNTER_VAL(a))

#define COUNTER_DIFF(a, b) \
    (COUNTER(a)-COUNTER(b))

/* ==================== GNU C and possibly other UNIX compilers ===================== */
#if !defined(WIN32) || defined(__GNUC__)

typedef union {
  myInt64 int64;
  struct { INT32 lo, hi; } int32;
} tsc_counter;

#define RDTSC(cpu_c) \
      ASM VOLATILE ("rdtsc" : "=a" ((cpu_c).int32.lo), "=d"((cpu_c).int32.hi))
#define CPUID() \
        ASM VOLATILE ("cpuid" : : "a" (0) : "bx", "cx", "dx" )

/* ======================== WIN32 ======================= */
#else

typedef union
    {       myInt64 int64;
            struct {INT32 lo, hi;} int32;
    } tsc_counter;

#define RDTSC(cpu_c)   \
    {       __asm rdtsc    \
            __asm mov (cpu_c).int32.lo,eax  \
            __asm mov (cpu_c).int32.hi,edx  \
    }

#define CPUID() \
    { \
        __asm mov eax, 0 \
        __asm cpuid \
    }

#endif

void init_tsc() {
  ; // no need to initialize anything for x86
}

myInt64 start_tsc(void) {
  tsc_counter start;
  CPUID();
  RDTSC(start);
  return COUNTER_VAL(start);
}

myInt64 stop_tsc(myInt64 start) {
  tsc_counter end;
  RDTSC(end);
  CPUID();
  return COUNTER_VAL(end) - start;
}
} // namespace

using bvh_func = int (*)(struct BVHPointer, struct BVHPointer);

using namespace ptc;

//TEST(TestPTC, FooTest) {
//  std::cout << "FooTest" << std::endl;
//
//  EXPECT_EQ(4, 4);
//}

ContractionData create_contraction_data() {
//  std::unordered_map<int, int> iteration_variables;
//  iteration_variables[0] = 0;//"i";
//  iteration_variables[1] = 1;//"j";
//  iteration_variables[2] = 2;//"k";
//  iteration_variables[3] = 3;//"l";
//
//  slice iteration_var_ranges;
//  iteration_var_ranges[0] = index_range{0, 3};
//  iteration_var_ranges[1] = index_range{0, 4};
//  iteration_var_ranges[2] = index_range{0, 4};
//  iteration_var_ranges[3] = index_range{0, 8};
//
//  /*iteration_var_ranges["i"] = index_range{0, 4};
//  iteration_var_ranges["j"] = index_range{0, 4};
//  iteration_var_ranges["k"] = index_range{0, 4};
//  iteration_var_ranges["l"] = index_range{0, 8};*/
//
//  tc_metadata.iteration_variable_ids = iteration_variables;
//  tc_metadata.iteration_var_ranges = iteration_var_ranges;
  std::vector<int> rankIDs{0, 1, 2, 3};
  std::vector<int> dims{0, 0, 0, 0};
  std::vector<Slice> s{{{0, 3}, {0, 4}, {0, 4}, {0, 8}}};

  std::vector<std::vector<int>> inputRankIDs{};
  std::vector<int> outputRankIDs{};
  std::vector<std::vector<int>> inputDims{};
  std::vector<int> outputDims{};
  std::vector<std::vector<Slice>> inputRanges{};
  std::vector<Slice> outputRanges{};
  // local output slice dimensions: [3,4,4,8]
  std::vector<std::vector<int>> iteration_var_limits{{(3 - 0) - 1, (4 - 0) - 1, (4 - 0) - 1, (8 - 0) - 1}};
  std::vector<DistributionData> distribution{};
  ReductionData reduction{nullptr, nullptr};
  int index_count = 4;

  ContractionData tc_metadata
      {inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges, outputRanges, iteration_var_limits,
       distribution, reduction,
       index_count};

  return tc_metadata;
}

TEST(TestPTC, End_to_End) {
  MyMPI m{nullptr, nullptr};

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

  int rank = m.get_rank();

  // This vector gets initialized locally for each processor (with its own local pointers)

  // Only rank 0 starts knowing the tensors. It has to distribute them to the other ranks first.
  data_type* rt_0 = rank != 0? nullptr : a;
  data_type* rt_1 = rank != 0? nullptr : b;
  data_type* rt_2 = rank != 0? nullptr : c;

  std::vector<data_type*> ssv(3); // 3 inputs
  for (int i = 0; i < ssv.size(); ++i) {
    std::vector<int> subsizes{};
    subsizes.reserve(inputRanges[rank][i].size());
    std::transform(inputRanges[rank][i].begin(), inputRanges[rank][i].end(), std::back_inserter(subsizes), [](std::pair<size_t, size_t> p) {
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
  std::transform(outputRanges[rank].begin(), outputRanges[rank].end(), std::back_inserter(subsizes), [](std::pair<size_t, size_t> p) {
    return p.second - p.first;
  });
  int reduce_local_size = std::reduce(subsizes.begin(), subsizes.end(), 1, std::multiplies<>());
  auto* reduce_local = static_cast<data_type*>(calloc(reduce_local_size, sizeof(data_type)));

  int reduce_final_size = std::reduce(outputDims.begin(), outputDims.end(), 1, std::multiplies<>());
  auto* reduce_final = static_cast<data_type*>(calloc(reduce_final_size, sizeof(data_type)));

  ReductionData reduction{reduce_final, reduce_local};
  int index_count = 2;

  ContractionData tc_metadata
      {inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges, outputRanges, iteration_var_limits,
       distribution, reduction,
       index_count};

  PTC::distribute(tc_metadata);
  PTC::localContraction(tc_metadata);
  PTC::reduce(tc_metadata);

  if (rank == 0) {
    std::cout << "result:\n";
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 4; ++j) {
        std::cout << reduce_final[i * 4 + j] << " ";
      }
      std::cout << "\n";
    }
    std::cout << std::endl;
  }

// expected output:
// array([[1.95179666, 3.90430684, 3.47275307, 3.88317959],
//       [1.99828928, 2.95809314, 3.42278582, 2.86400505],
//       [2.24069111, 4.08175584, 3.86049226, 3.61600952]])
  for (auto ptr : ssv) free(ptr);
  free(reduce_local);
  free(reduce_final);
}

//#define TESTCONTRACTION
#ifdef TESTCONTRACTION

TEST(TestPTC, TestMultiIndex) {
  MPI_Init(nullptr, nullptr); // ugly, but ok

  ContractionData tc_metadata = create_contraction_data();
  MultiIndex multi_index{tc_metadata};

  std::cout << multi_index.canIterate() << std::endl;
  int iter_count = 0;
  while (multi_index.canIterate()) {
    iter_count++;
    multi_index.iterate();
  }
  std::cout << iter_count << std::endl;
}


// Currently, we probably support all of the operations kmario23 mentioned on
// https://stackoverflow.com/questions/26089893/understanding-numpys-einsum
TEST(TestPTC, i_ij_INTO_i) {

  std::cout << "i,ij->i" << std::endl;
  // Input 1
  data_type input_0[3] = {0, 1, 2};
  std::vector<int> rankIDs_0{0};
  std::vector<int> localDims_0{3};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Input 2
  data_type input_1[12] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}; //{{0, 1, 2, 3}, {4, 5, 6, 7}, {8, 9, 10, 11}};
  std::vector<int> rankIDs_1{0, 1};
  std::vector<int> localDims_1{3, 4};
  ptc::LocalData<false> localData_1{input_1, rankIDs_1, localDims_1};
  std::cout << "Created object 1 successfully" << std::endl;

  // Create Tensor Contraction metadata object

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"i";
  iteration_variables[1] = 1;//"j";

//  slice iteration_var_ranges;
//  iteration_var_ranges[0] = index_range{0, 3};
//  iteration_var_ranges[1] = index_range{0, 4};

  std::vector<std::vector<int>> inputRankIDs{rankIDs_0, rankIDs_1};
  std::vector<int> outputRankIDs{0};
  std::vector<std::vector<int>> inputDims{{3}, {3, 4}};
  std::vector<int> outputDims{3};
  std::vector<std::vector<Slice>> inputRanges{
      {
          {{0, 3}},
          {{0, 3}, {0, 4}}
      }
  };
  std::vector<Slice> outputRanges{{{0, 3}}};
  // again the dimensions. there might be quite the redundancy between this and input/outputRanges
  std::vector<std::vector<int>> iteration_var_limits{{3, 4}};
  // This vector gets initialized differently for each processor (with its own local pointers)
  std::vector<DistributionData> distribution{{nullptr, input_0}, {nullptr, input_1}};
  ReductionData reduction{nullptr, nullptr};
  int index_count = 2;

  ContractionData tc_metadata
      {inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges, outputRanges, iteration_var_limits,
       distribution, reduction,
       index_count};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  ptc::LocalData output = PTC::localContraction(tc_metadata);

  for (int i = 0; i < 3; i++) {
    std::cout << output.data[i] << std::endl;
  }

  std::cout << "Works fine" << std::endl;
  // Expected Output: [ 0, 22, 76]

  // TODO maybe automatic value checking
  EXPECT_EQ(4, 4);
}

// Batch matrix multiplication
TEST(TestPTC, bij_bjk_bik) {
  std::cout << "bij, bjk -> bik" << std::endl;
  // Input create input 0
  data_type input_0[32] = {11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44,
                           1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 1, 2};
  std::vector<int> localDims_0{2, 4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Input create input 1
  data_type input_1[32] = {11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44,
                           1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_1{0, 2, 3};
  std::vector<int> localDims_1{2, 4, 4};
  ptc::LocalData<false> localData_1{input_1, rankIDs_1, localDims_1};
  std::cout << "Created object 1 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs{0, 1, 3};

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"b";
  iteration_variables[1] = 1;//"i";
  iteration_variables[2] = 2;//"j";
  iteration_variables[3] = 3;//"k";

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 2};
  iteration_var_ranges[1] = index_range{0, 4};
  iteration_var_ranges[2] = index_range{0, 4};
  iteration_var_ranges[3] = index_range{0, 4};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));
  ptc1.addLocalInput(std::move(localData_1));

  ptc::LocalData output = ptc1.localContraction();

  for (int i = 0; i < 32; i++) {
    std::cout << output.data[i] << std::endl;
  }

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;
  /* Expected Output:
  [[[1350, 1400, 1450, 1500],
  [2390, 2480, 2570, 2660],
  [3430, 3560, 3690, 3820],
  [4470, 4640, 4810, 4980]],

  [[  10,   10,   10,   10],
  [  20,   20,   20,   20],
  [  30,   30,   30,   30],
  [  40,   40,   40,   40]]]*/
}

// Sum along y axis
TEST(TestPTC, ij_INTO_j) {
  std::cout << "ij -> j" << std::endl;
  // Input create input 0
  data_type input_0[16] = {1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 1};
  std::vector<int> localDims_0{4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs{1};

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"b";
  iteration_variables[1] = 1;//"i";

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 4};
  iteration_var_ranges[1] = index_range{0, 4};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));

  ptc::LocalData output = ptc1.localContraction();

  for (int i = 0; i < 4; i++) {
    std::cout << output.data[i] << std::endl;
  }

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;
  // Expected Output: [10, 10, 10, 10]
}

// NOT mtt-krp, see the last test (below)
TEST(TestPTC, ijk_il_jl_INTO_il) {
  std::cout << "ijk, il, jl -> il" << std::endl;
  // Input create input 0
  data_type input_0[32] = {11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 1, 2};
  std::vector<int> localDims_0{2, 4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Input create input 1
  data_type input_1[12] = {11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43};
  std::vector<int> rankIDs_1{1, 3};
  std::vector<int> localDims_1{4, 3};
  ptc::LocalData<false> localData_1{input_1, rankIDs_1, localDims_1};
  std::cout << "Created object 1 successfully" << std::endl;

  // Input create input 2
  data_type input_2[12] = {1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4};
  std::vector<int> rankIDs_2{2, 3};
  std::vector<int> localDims_2{4, 3};
  ptc::LocalData<false> localData_2{input_2, rankIDs_2, localDims_2};
  std::cout << "Created object 2 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs{0, 3};

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//i
  iteration_variables[1] = 1;//j
  iteration_variables[2] = 2;//k
  iteration_variables[3] = 3;//l

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 2};
  iteration_var_ranges[1] = index_range{0, 4};
  iteration_var_ranges[2] = index_range{0, 4};
  iteration_var_ranges[3] = index_range{0, 3};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));
  ptc1.addLocalInput(std::move(localData_1));
  ptc1.addLocalInput(std::move(localData_2));

  ptc::LocalData output = ptc1.localContraction();

  for (int i = 0; i < 6; i++) {
    std::cout << output.data[i] << std::endl;
  }

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;

  /* Expected Output:
  [[34120 35240 36360]
  [ 3100  3200  3300]] */
}

// Extract diagonal elements
TEST(TestPTC, ii_INTO_j) {
  std::cout << "ii -> j" << std::endl;
  // Input create input 0
  data_type input_0[16] = {1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 0};
  std::vector<int> localDims_0{4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs{0};

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"b";

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 4};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));

  ptc::LocalData output = ptc1.localContraction();

  for (int i = 0; i < 4; i++) {
    std::cout << output.data[i] << std::endl;
  }

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;
  // Expected Output: [1, 2, 3, 4]
}

// Sum diagonal elements
TEST(TestPTC, ii_INTO_) {
  std::cout << "ii -> " << std::endl;
  // Input create input 0
  data_type input_0[16] = {1, 1, 1, 1, 2, 1, 2, 2, 3, 3, 1, 3, 4, 4, 4, 1};
  std::vector<int> rankIDs_0{0, 0};
  std::vector<int> localDims_0{4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs;

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"b";

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 4};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));

  ptc::LocalData output = ptc1.localContraction();

  std::cout << *(output.data) << std::endl;

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;
  // Expected Output: 4
}

// Sum all of the elements of a matrix
TEST(TestPTC, ij_INTO_) {
  std::cout << "ij -> " << std::endl;
  // Input create input 0
  data_type input_0[16] = {1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 1};
  std::vector<int> localDims_0{4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs;

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//"b";
  iteration_variables[1] = 1;

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 4};
  iteration_var_ranges[1] = index_range{0, 4};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));

  ptc::LocalData output = ptc1.localContraction();

  std::cout << *(output.data) << std::endl;

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;
  // Expected Output: 40
}

// actual MTT-KRP
TEST(TestPTC, mtt_krp) {
  std::cout << "MTT-KRP: ijk, kl, jl -> il" << std::endl;
  // Input create input 0
  data_type input_0[32] = {11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4};
  std::vector<int> rankIDs_0{0, 1, 2};
  std::vector<int> localDims_0{2, 4, 4};
  ptc::LocalData<false> localData_0{input_0, rankIDs_0, localDims_0};
  std::cout << "Created object 0 successfully" << std::endl;

  // Input create input 1
  data_type input_1[12] = {11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43};
  std::vector<int> rankIDs_1{2, 3};
  std::vector<int> localDims_1{4, 3};
  ptc::LocalData<false> localData_1{input_1, rankIDs_1, localDims_1};
  std::cout << "Created object 1 successfully" << std::endl;

  // Input create input 2
  data_type input_2[12] = {1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4};
  std::vector<int> rankIDs_2{1, 3};
  std::vector<int> localDims_2{4, 3};
  ptc::LocalData<false> localData_2{input_2, rankIDs_2, localDims_2};
  std::cout << "Created object 2 successfully" << std::endl;

  // Create Tensor Contraction metadata object
  std::vector<int> outputRankIDs{0, 3};

  std::unordered_map<int, int> iteration_variables;
  iteration_variables[0] = 0;//i
  iteration_variables[1] = 1;//j
  iteration_variables[2] = 2;//k
  iteration_variables[3] = 3;//l

  slice iteration_var_ranges;
  iteration_var_ranges[0] = index_range{0, 2};
  iteration_var_ranges[1] = index_range{0, 4};
  iteration_var_ranges[2] = index_range{0, 4};
  iteration_var_ranges[3] = index_range{0, 3};

  ContractionData tc_metadata{iteration_variables, outputRankIDs, iteration_var_ranges};

  // Create partial tensor contraction object
  ptc::PTC ptc1{tc_metadata};

  // Add local inputs to ptc object
  ptc1.addLocalInput(std::move(localData_0));
  ptc1.addLocalInput(std::move(localData_1));
  ptc1.addLocalInput(std::move(localData_2));

  ptc::LocalData output = ptc1.localContraction();

  for (int i = 0; i < 6; i++) {
    std::cout << output.data[i] << std::endl;
  }

  // Probably should have an assert here instead xd
  std::cout << "Works fine" << std::endl;

  /* Expected Output:
  [[34300 35600 36900]
  [ 3120  3240  3360]] */

  // This is the last test in this TestPTC.cpp file
  MPI_Finalize();
}

#endif

} // namespace test
