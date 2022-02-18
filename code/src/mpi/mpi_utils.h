#pragma once

#include <vector>
#include <cassert>
#include "mpi.h"

#include <iostream>

class MyMPI {
  int rank, num_procs;
 public:
  MyMPI (int* argc = NULL, char*** argv = NULL) {
    MPI_Init(argc, argv);
    MPI_Comm_size(MPI_COMM_WORLD, &num_procs);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  }

  /// Get the global rank (process ID)
  int get_rank() const noexcept {
    return rank;
  }

  /// Get the number of processes
  int get_num_procs() const noexcept {
    return num_procs;
  }

  ~MyMPI() {
    MPI_Finalize();
  }
};

class MyMPI_Group {
  MPI_Group group;
 public:
  /// The communicator group (contains all processes within comm)
  explicit MyMPI_Group(MPI_Comm comm) {
    MPI_Comm_group(comm, &group);
  }

  /// Make a new group (subset of base_group) containing only procs with ID's in ranks
  MyMPI_Group(MyMPI_Group&& base_group, const std::vector<int>& ranks) {
    MPI_Group_incl(std::move(base_group), ranks.size(), ranks.data(), &group);
  }

  MyMPI_Group(MyMPI_Group&& other) {
    group = other.group;
    other.group = MPI_GROUP_NULL;
  }

  MyMPI_Group& operator=(MyMPI_Group&& other) {
    assert(this != &other);

//    if (group != MPI_GROUP_NULL) MPI_Group_free(&group);

    group = other.group;
    other.group = MPI_GROUP_NULL;

    return *this;
  }

  MyMPI_Group(const MyMPI_Group&) = delete;
  MyMPI_Group& operator=(const MyMPI_Group&) = delete;

  operator MPI_Group () const noexcept {
    return group;
  }

  ~MyMPI_Group() {
//    if (group != MPI_GROUP_NULL) MPI_Group_free(&group);
  }
};

class MyMPI_Comm {
  MPI_Comm comm;
  int rank, num_procs;

  void init_data() {
    // Is calling process even contained?
    if (comm == MPI_COMM_NULL) return;
    MPI_Comm_size(comm, &num_procs);
    MPI_Comm_rank(comm, &rank);
  }

 public:
  /// Implicit conversion from MPI_Comm
  MyMPI_Comm(MPI_Comm comm): comm{comm} {
    init_data();
  }

  /// color determines what communicator our process is assigned to.
  /// new_id will be used to order the processes within the new comm(s)
  /// tie-breaker is the id in the old communicator.
  /// old communicator is COMM_WORLD by default.
  MyMPI_Comm (int color, int my_id, MPI_Comm old_comm) {
    MPI_Comm_split(old_comm, color, my_id, &comm);

    init_data();
  }

  /// Efficiently make a new communicator containing only procs with ID's in selected_ranks
  MyMPI_Comm(const std::vector<int>& selected_ranks, MPI_Comm old_comm) {
    MyMPI_Group old_group{old_comm};
    MyMPI_Group selected_group{std::move(old_group), selected_ranks};
    MPI_Comm_create(old_comm, std::move(selected_group), &comm);

    init_data();
  }

  /// Make a new communicator given a group that's a subset of the group of old_comm
  MyMPI_Comm(MPI_Group group, MPI_Comm old_comm) {
    MPI_Comm_create(old_comm, group, &comm);
  }

  MyMPI_Comm(const MyMPI_Comm&) = delete;
  MyMPI_Comm& operator=(const MyMPI_Comm&) = delete;

  MyMPI_Comm(MyMPI_Comm&& other) {
    comm = other.comm;
    rank = other.rank;
    num_procs = other.num_procs;
    other.comm = MPI_COMM_NULL;
  }

  MyMPI_Comm& operator=(MyMPI_Comm&& other) {
    assert(this != &other);

//    if (comm != MPI_COMM_NULL && comm != MPI_COMM_WORLD) MPI_Comm_free(&comm);

    comm = other.comm;
    rank = other.rank;
    num_procs = other.num_procs;
    other.comm = MPI_COMM_NULL;

    return *this;
  }

  /// Is the process calling this method even contained within this communiator?
  bool contains_caller() const noexcept {
    return comm != MPI_COMM_NULL;
  }

  /// Get the rank (process ID) within the new communicator
  int get_comm_rank() const noexcept {
    assert(comm != MPI_COMM_NULL);
    return rank;
  }

  /// Get the number of processes within the new communicator
  int get_comm_size() const noexcept {
    assert(comm != MPI_COMM_NULL);
    return num_procs;
  }

  /// Implicit conversion to MPI_Comm
  operator MPI_Comm() const noexcept {
    return comm;
  }

  ~MyMPI_Comm() {
//    if (comm != MPI_COMM_NULL && comm != MPI_COMM_WORLD) MPI_Comm_free(&comm);
  }
};
