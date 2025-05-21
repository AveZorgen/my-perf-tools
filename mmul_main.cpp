#include <dlfcn.h>

#include <iostream>
#include <string>
#include <vector>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <library_path>" << std::endl;
        return 1;
    }

    constexpr int n = 1536; 1 << 11;
    std::vector<float> a(n * n);
    std::vector<float> b(n * n);
    std::vector<float> c(n * n, 0.0f);

    for (int i = 0; i < n; i++) {
        a[i] = i;
        b[i] = i + 1;
    }

    void* handle = dlopen(argv[1], RTLD_LAZY);
    if (!handle) {
        std::cerr << "Error loading library: " << dlerror() << std::endl;
        return 1;
    }

    using MatMulFunc = void (*)(float*, float*, float*, int);
    MatMulFunc matmul = reinterpret_cast<MatMulFunc>(dlsym(handle, "matmul"));
    if (!matmul) {
        std::cerr << "Error loading function: " << dlerror() << std::endl;
        dlclose(handle);
        return 1;
    }

    const int bigger_than_cachesize = 10 * 1024 * 1024;
    long* p = new long[bigger_than_cachesize];

    for (int i = 0; i < bigger_than_cachesize; i++) {
        p[i] = rand();
    }

    matmul(a.data(), b.data(), c.data(), n);

    dlclose(handle);

    return 0;
}