#ifdef __cplusplus
extern "C" {
#endif

void matmul(float *A, float *B, float *C, int N);

#ifdef __cplusplus
}
#endif

void matmul(float *A, float *B, float *C, int N) {
    for (int i = 0; i < N; i++) {
        for (int k = 0; k < N; k++) {
            float a_ik = A[i * N + k];
            for (int j = 0; j < N; j++) {
                C[i * N + j] += a_ik * B[k * N + j];
            }
        }
    }
}