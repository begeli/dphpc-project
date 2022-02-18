#include "data_reader.h"

// TODO: Implement the data reader

Data_Reader::Data_Reader() {}

Data_Reader::~Data_Reader() {}

void Data_Reader::read_tc_parameters_from_file(std::string path) {}

void Data_Reader::read_d_parameters_from_file(std::string path) {}

void Data_Reader::read_data_from_file(std::string path) {}

void Data_Reader::generate_data(std::unordered_set<std::string> ranks,
                                std::unordered_map<std::string, int> dimensions,
                                std::string streaming_dir) {}

//struct Data Data_Reader::get_data() {
//    return Data_Reader::data;
//}

//struct ContractionData Data_Reader::get_tc_data() {
//    return Data_Reader::tc_data;
//}