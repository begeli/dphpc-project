#pragma once

#include <utility>
#include <vector>

#include "metadata.h"
#include "MultiIndex.h"
#include "../mpi/mpi_utils.h"

#include "LocalData.h"

#define TC_COMM_COUNTERS

size_t tc_bytes_sent_bcast = 0;
size_t tc_bytes_sent_reduce = 0;

namespace ptc {

void distribute(const ContractionData& data, const MyMPI_Comm& comm);
LocalData localContraction(const ContractionData& data, const MyMPI_Comm& comm);
void reduce(const ContractionData& data, const MyMPI_Comm& comm);

/**
 * This is the only method "users" will need to call.
 * Performs distribution, local contraction and reduction.
 *
 * @param data This is the object containing all relevant information (like dimensions, processor count ...)
 *             See metadata.h for more details.
 * */
template<bool doDistribution>
LocalData contractTensors(const ContractionData& data,
                          const MyMPI_Comm& comm = MPI_COMM_WORLD) {
#ifdef TC_COMM_COUNTERS
  tc_bytes_sent_bcast = 0;
  tc_bytes_sent_reduce = 0;
#endif
  if constexpr (doDistribution) distribute(data, comm);
  std::cout << "["<< comm.get_comm_rank() << "] Distribution done..." << std::endl;
#ifdef TC_COMM_COUNTERS
  std::cout << "[" << comm.get_comm_rank() << "] Distribution Bytes sent: " << tc_bytes_sent_bcast << std::endl;
#endif
  LocalData output = localContraction(data, comm);
  std::cout << "["<< comm.get_comm_rank() << "] Local contraction done..." << std::endl;
  reduce(data, comm);
  std::cout << "["<< comm.get_comm_rank() << "] Reduce done..." << std::endl;
#ifdef TC_COMM_COUNTERS
  std::cout << "[" << comm.get_comm_rank() << "] Reduction Bytes sent: " << tc_bytes_sent_reduce << std::endl;
#endif

  return output; // copy elision
}

} // namespace ptc
