# -*- coding: utf-8 -*-
# !/usr/bin/env python

import numpy as np
import scipy.io as sio
from scipy import signal
import os
from util import config, preprocessing, featex, offline, performance
import matplotlib.pyplot as plt


def apply_method(data, windowSize, segmenting, criterion, method, prot_iterations, prot_period):
    if segmenting == 'sliding':
        label = offline.make_label_windows(prot_iterations, prot_period, windowSize, len(FREQUENCIES))
        windows = offline.extract_windowed_segment(data, windowSize, prot_period, FS)
    elif segmenting == 'nooverlap':
        label = offline.make_label_segments(prot_iterations, prot_period, windowSize, len(FREQUENCIES))
        windows = offline.extract_segment_start(data, windowSize, prot_period, FS)
    else:
        raise AttributeError

    if criterion == 'offline':
        o = offline.offline_classify(windows, FREQUENCIES, method)
        cm = performance.get_confusion_matrix(label, o, len(FREQUENCIES))
        return performance.get_accuracy(cm), 0
        # return performance.get_cohen_k(cm), 0
    elif criterion == 'pseudoon':
        o, avg_time = offline.pseudo_online_classify(windows, FREQUENCIES, FS, method, pause=0, period=prot_period)
        cm = performance.get_confusion_matrix(label, o, len(FREQUENCIES))
        return performance.get_accuracy(cm), avg_time
    else:
        raise AttributeError


def perform(name):
    """
    Perform preprocessing and classification using one method and one window length
    Return a matrix: acc = accuracy und = undefinedRate
    [20 acc20 und20
     10 acc10 und10
     5 acc5 und5]
    """
    # read data
    data = sio.loadmat(os.path.join(config.DATA_PATH, name))
    X = data['data']

    # CAR FILTER & PASSBAND FILTER
    Wcritic = np.array([0., 4., 5., 49., 50., 300.])
    b, a = preprocessing._get_fir_filter(Wcritic, FS, 851)
    X = signal.fftconvolve(X, b[:, np.newaxis], mode='valid')

    X -= X.mean(axis=0)
    X = np.dot(X, preprocessing.CAR(X.shape[1]))

    chans = np.in1d(config.SENSORS_SANDRA, CHANNELS)
    _ = X[0:160 * FS, chans].reshape(160 * FS, len(CHANNELS))  # protocol first part, 20s x 2
    y2 = X[160 * FS: 320 * FS, chans].reshape(160 * FS, len(CHANNELS))  # protocol second part, 10s x 4
    y3 = X[320 * FS: 420 * FS, chans].reshape(X.shape[0] - 320 * FS, len(CHANNELS))  # protocol third part, 5s x 5

    # Plotting spectrum to observe power distribution
    # f,psd = preprocessing.get_psd(y1[:,0], 3, Fs)
    # plt.plot(f,psd)
    # plt.show()

    # Comparison parameters
    # criterion == 'offline' -> classifier just a criterion of maxima. Windows->Output 1:1
    # criterion == 'pseudoon' -> classifier with a confidence criterion. Windows->Output 1:(0|1)
    criterion = 'pseudoon'
    # segment == 'sliding' -> sliding windows with slide = 1 s
    # segment == 'nooverlap' -> windows with no overlap. Only the first and, if present, the second, are considered
    segmenting = 'sliding'
    method = METHOD(list(FREQUENCIES), (WINLENGTH - 1) * FS, FS)

    records = np.zeros((2, 5))

    acc, avg_time = apply_method(y2, WINLENGTH, segmenting, criterion, method, prot_iterations=4, prot_period=10)
    # avg_time = WINLENGTH + und / (1 - und)
    itr = performance.get_ITR(4, acc, avg_time) * 60
    ut = performance.get_utility(6, acc, avg_time) * 60
    records[0, :] = [10, 100 * acc, avg_time, itr, ut]
    print '##'

    acc, avg_time = apply_method(y3, WINLENGTH, segmenting, criterion, method, prot_iterations=5, prot_period=5)
    # avg_time = WINLENGTH + und / (1 - und)
    itr = performance.get_ITR(4, acc, avg_time) * 60
    ut = performance.get_utility(6, acc, avg_time) * 60
    records[1, :] = [5, 100 * acc, avg_time, itr, ut]
    print '##'

    return records


if __name__ == '__main__':
    FREQUENCIES = [5.6, 6.4, 6.9, 8]
    FS = 600

    CHANNELS = ['Oz', 'O2', 'O1']
    METHOD = featex.CCA

    for WINLENGTH in [2, 3, 4, 5]:
        data = np.zeros((len(config.SUBJECTS_SANDRA), 2, 5))
        for ii, name in enumerate(config.SUBJECTS_SANDRA):
            DATA_FILE = "protocolo 7/%s_prot7_config1.mat" % name
            data[ii, :, :] = perform(DATA_FILE)

        filename = "sandra_CCA_" + str(CHANNELS) + "_" + str(WINLENGTH) + ".txt"
        data = data.reshape(len(config.SUBJECTS_SANDRA) * 2, 5)
        np.savetxt(filename, data, fmt="%.2f", delimiter=',')
