#include <cstdlib>
#include <iostream>
#include <theora/theora.h>

int main()
{
    std::cout << "theora version: " << theora_version_string() << std::endl;
    return EXIT_SUCCESS;
}
