#ifdef __cplusplus
extern "C" {
#endif

void matmul(float *A, float *B, float *C, int N);

#ifdef __cplusplus
}
#endif
#define BLOCK_SIZE 32

void matmul(float *A, float *B, float *C, int N) {
    for (int ii = 0; ii < N; ii += BLOCK_SIZE) {
        for (int jj = 0; jj < N; jj += BLOCK_SIZE) {
            for (int kk = 0; kk < N; kk += BLOCK_SIZE) {
                for (int i = ii; i < ii + BLOCK_SIZE; i++) {
                    for (int k = kk; k < kk + BLOCK_SIZE; k++) {
                        float a_ik = A[i * N + k];
                        for (int j = jj; j < jj + BLOCK_SIZE; j++) {
                            C[i * N + j] += a_ik * B[k * N + j];
                        }
                    }
                }
            }
        }
    }
}