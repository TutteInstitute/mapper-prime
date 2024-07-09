''' modified: 2024-07-04 ~10am'''
import fast_hdbscan ## This is the modified local copy!

import sys
import numpy as np
import pandas as pd
import math
import numba
from tqdm import tqdm, trange
from warnings import warn

def gaussian(t0, t, density, binwidth, epsilon = 0.01, params=None):
    K = -np.log(epsilon)/((binwidth/2)**2) 
    return np.exp(-K*(density*(t-t0))**2)

def square(t0, t, density, binwidth, epsilon = 0.1, params=(1,)):
    if params == None:
        print("Warning: Your kernel has parameters but you didn't pass any.")
    overlap, = params
    distance = (t-t0)
    out = (np.abs(distance)<((1+overlap)*np.sqrt(
        binwidth/(4*density)
    ))).astype(int)
    return out

def square_nodensity(t0, t, density, binwidth, epsilon = 0.1, params=(1,)):
    if params == None:
        print("Warning: Your kernel has parameters but you didn't pass any.")
    overlap, = params
    distance = (t-t0)
    out = (np.abs(distance)<((1+overlap)*binwidth/2)).astype(int)
    return out
    
def window(distance, width=1):
    distance[np.abs(distance)>=width] = 0
    distance[np.abs(distance)<width] = (1/2)*(1+np.cos(np.pi*distance/width))

def compute_point_rates(data, time, distances, width):
    lambdas = np.zeros(np.size(time))
    for i,d in tqdm(enumerate(distances), desc='Computing f-rates'):
        t0 = time[i]
        idx=(d<=width).nonzero()[0]
        vals_in_series = time[idx]
        vals_in_series.sort()
        t0_index = np.squeeze(np.where(vals_in_series == t0))
        deltas=np.diff(vals_in_series)
        np.roll(deltas, -t0_index)
        N=np.size(deltas)
        time_weights = np.zeros(N)
        for k, _ in enumerate(deltas):
            time_weights[k] = min(
                [k, np.abs(k-(N-1))]
            )
        time_weights = np.exp(-time_weights)
        if np.size(idx)==1:
            lambdas[i] = np.inf
        else:
            lambdas[i] = np.average(deltas, weights=time_weights)
            
    return lambdas


def weighted_clusters(
    data,
    time,
    checkpoints,
    densities,
    clusterer,
    kernel,
    kernel_params=None,
    eps = 0.01
):
    # -2 as a placeholder for "not clustered"
    clusters = np.ones((np.size(checkpoints), np.size(time)),dtype=int)*-2
    weights =  np.zeros((np.size(checkpoints), np.size(time)))
                                     
    cp_with_ends = [np.amin(time)]+list(checkpoints)+[np.amax(time)]
    for idx, t0 in enumerate(checkpoints):
        bin_width = (cp_with_ends[idx+2]-cp_with_ends[idx])/2
        if kernel_params == None:
            for i in np.arange(np.size(time)):
                weights[idx,i] = kernel(
                    t0, time[i], densities[i], bin_width,
                )
        else:
            for i in np.arange(np.size(time)):
                weights[idx,i] = kernel(
                    t0, time[i], densities[i], bin_width, params=kernel_params,
                )
        slice_ = (weights[idx] >= eps).nonzero()
        slice_ = np.squeeze(slice_)
        data_slice = data[slice_]
        if data[slice_].ndim == 1:
            data_slice = data_slice.reshape(-1,1)
        
        cluster_labels = clusterer.fit(data_slice, sample_weight=weights[idx,slice_]).labels_
        clusters[idx, slice_] = cluster_labels
    
    return clusters, weights
