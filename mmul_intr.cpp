#ifdef __cplusplus
extern "C" {
#endif

void matmul(float *A, float *B, float *C, int N);

#ifdef __cplusplus
}
#endif

#include <immintrin.h>
#define BLOCK_SIZE 64

void matmul(float *A, float *B, float *C, int N) {
    for (int ii = 0; ii < N; ii += BLOCK_SIZE) {
        for (int jj = 0; jj < N; jj += BLOCK_SIZE) {
            for (int kk = 0; kk < N; kk += BLOCK_SIZE) {
                for (int i = ii; i < ii + BLOCK_SIZE && i < N; i++) {
                    for (int k = kk; k < kk + BLOCK_SIZE && k < N; k++) {
                        __m256 a = _mm256_set1_ps(A[i * N + k]);
                        for (int j = jj; j < jj + BLOCK_SIZE && j < N; j += 8) {
                            __m256 b = _mm256_loadu_ps(&B[k * N + j]);
                            __m256 c = _mm256_loadu_ps(&C[i * N + j]);
                            __m256 product = _mm256_mul_ps(a, b);
                            c = _mm256_add_ps(product, c);
                            _mm256_storeu_ps(&C[i * N + j], c);
                        }
                    }
                }
            }
        }
    }
}