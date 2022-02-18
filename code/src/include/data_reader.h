#ifndef TC_DATA_READER_H
#define TC_DATA_READER_H

#include <unordered_map>
#include <unordered_set>
#include <string>
#include "metadata.h"

/**
 * A class to read data from a file or generate the data.
 * */
class Data_Reader {
    public:
        Data_Reader();

        ~Data_Reader();

        /**
         * Read the partition information of the python script from a file
         * */
        void read_tc_parameters_from_file(std::string path);

        /**
         * Read the partition information of the python script from a file
         * TODO: (Does data have separate parameters?)
         * */
        void read_d_parameters_from_file(std::string path);

        /**
         * Read the container data from a file
         * Parameters should read from a file first
         * */
        void read_data_from_file(std::string path);

        /**
         * Generate the container data (Not needed if we read it from a file)
         * TODO: Probably isn't useful beyond testing purposes
         * */
        void generate_data(std::unordered_set<std::string> ranks,
                           std::unordered_map<std::string, int> dimensions,
                           std::string streaming_dir);

        /**
         * Return the container that holds the data for a matrix/tensor
         * that will be used in the tensor contraction
         * */
        struct Data get_data();

        /**
         * Return the container that holds metadata about the tensor contraction
         * */
        struct ContractionData get_tc_data();
    private:
        //struct Data data;
        //struct ContractionData tc_data;
};

#endif //TC_DATA_READER_H
