#include <gtest/gtest.h>
#include <sys/resource.h>

#include "../src/include/metadata.h"
#include "../src/include/LocalData.h"

#define STACKSIZE 268435456
#define CORESIZE 268435456
// --------------------------------------------------------------------------
int main(int argc, char* argv[]) {
  struct rlimit rl;

  // Increase stack size to 256 MB -- not necessary, but might aswell.
  int result = getrlimit(RLIMIT_STACK, &rl);
  rl.rlim_cur = STACKSIZE;
  setrlimit(RLIMIT_STACK, &rl);

  // Increase core dump size from 0 -- just in case something goes wrong.
  result = getrlimit(RLIMIT_CORE, &rl);
  rl.rlim_cur = CORESIZE;
  setrlimit(RLIMIT_CORE, &rl);

  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
// --------------------------------------------------------------------------

