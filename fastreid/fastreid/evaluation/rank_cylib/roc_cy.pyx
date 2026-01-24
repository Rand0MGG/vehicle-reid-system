# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True
# credits: https://github.com/KaiyangZhou/deep-person-reid/blob/master/torchreid/metrics/rank_cylib/rank_cy.pyx

import cython
import faiss
import numpy as np
cimport numpy as np


"""
Compiler directives:
https://github.com/cython/cython/wiki/enhancements-compilerdirectives
Cython tutorial:
https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html
Credit to https://github.com/luzai
"""


# Main interface
# Modified for Windows: Removed explicit types in signature to allow auto-casting inside.
# This fixes the "Buffer dtype mismatch" error.
cpdef evaluate_roc_cy(distmat, q_pids, g_pids, q_camids, g_camids):

    # Explicitly cast inputs to ensure they match the C-types defined below
    distmat = np.asarray(distmat, dtype=np.float32)
    q_pids = np.asarray(q_pids, dtype=np.int64)
    g_pids = np.asarray(g_pids, dtype=np.int64)
    q_camids = np.asarray(q_camids, dtype=np.int64)
    g_camids = np.asarray(g_camids, dtype=np.int64)

    cdef long num_q = distmat.shape[0]
    cdef long num_g = distmat.shape[1]

    cdef:
        # Modified for Windows: changed long[:,:] to long long[:,:]
        long long[:,:] indices = np.argsort(distmat, axis=1)
        long long[:,:] matches = (np.asarray(g_pids)[np.asarray(indices)] == np.asarray(q_pids)[:, np.newaxis]).astype(np.int64)

        float[:] pos = np.zeros(num_q*num_g, dtype=np.float32)
        float[:] neg = np.zeros(num_q*num_g, dtype=np.float32)

        long valid_pos = 0
        long valid_neg = 0
        long ind

        long q_idx, q_pid, q_camid, g_idx
        
        # Modified for Windows: changed long[:] to long long[:]
        long long[:] order = np.zeros(num_g, dtype=np.int64)

        float[:] raw_cmc = np.zeros(num_g, dtype=np.float32) # binary vector, positions with value 1 are correct matches
        
        # Modified for Windows: changed long[:] to long long[:]
        long long[:] sort_idx = np.zeros(num_g, dtype=np.int64)

        long idx

    for q_idx in range(num_q):
        # get query pid and camid
        q_pid = q_pids[q_idx]
        q_camid = q_camids[q_idx]

        for g_idx in range(num_g):
            order[g_idx] = indices[q_idx, g_idx]
        num_g_real = 0

        # remove gallery samples that have the same pid and camid with query
        for g_idx in range(num_g):
            if (g_pids[order[g_idx]] != q_pid) or (g_camids[order[g_idx]] != q_camid):
                raw_cmc[num_g_real] = matches[q_idx][g_idx]
                sort_idx[num_g_real] = order[g_idx]
                num_g_real += 1

        q_dist = distmat[q_idx]

        for valid_idx in range(num_g_real):
            if raw_cmc[valid_idx] == 1:
                pos[valid_pos] = q_dist[sort_idx[valid_idx]]
                valid_pos += 1
            elif raw_cmc[valid_idx] == 0:
                neg[valid_neg] = q_dist[sort_idx[valid_idx]]
                valid_neg += 1

    cdef float[:] scores = np.hstack((pos[:valid_pos], neg[:valid_neg]))
    cdef float[:] labels = np.hstack((np.zeros(valid_pos, dtype=np.float32),
                                      np.ones(valid_neg, dtype=np.float32)))
    return np.asarray(scores), np.asarray(labels)


# Compute the cumulative sum
cdef void function_cumsum(cython.numeric[:] src, cython.numeric[:] dst, long n):
    cdef long i
    dst[0] = src[0]
    for i in range(1, n):
        dst[i] = src[i] + dst[i - 1]