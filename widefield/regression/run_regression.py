from widefield.regression.linregress import LinearRegression, RecurrentRegression
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import tables as tb
from sklearn.decomposition import PCA, FactorAnalysis


# Import
basepath = "/suppscr/riekesheabrown/kpchamp/data/m187474/150804/"
summary_data_path = basepath + "SummaryTimeSeries.pkl"
summary_data = pd.read_pickle(summary_data_path)
image_data_path = basepath + "data_detrend_mask.h5"

# replace NaNs with 0s
summary_data['behavioral_measurables']['running_speed'][np.where(np.isnan(summary_data['behavioral_measurables']['running_speed']))[0]] = 0

include_orientations = False
if include_orientations:
    # Get stimulus orientations into array
    stimulus_contrasts = np.squeeze(summary_data['session_dataframe'].as_matrix(columns=['Contrast']))
    stimulus_orientations = np.zeros(summary_data['stimulus'].shape)
    stimulus_orientations[np.where(summary_data['stimulus'] != 0)[0]] = np.squeeze(summary_data['session_dataframe'].as_matrix(columns=['Ori']))[np.where(stimulus_contrasts != 0)[0]]

    # Get regressors into format for regression
    regressor_data = np.vstack((stimulus_contrasts, stimulus_orientations, summary_data['behavioral_measurables']['licking'],
                                summary_data['behavioral_measurables']['rewards'], summary_data['behavioral_measurables']['running_speed'])).T
    X_labels = ['stimulus contrast', 'stimulus orientation', 'licking', 'rewards', 'running speed']
else:
    # Get regressors into format for regression
    regressor_data = np.vstack((summary_data['stimulus'], summary_data['behavioral_measurables']['licking'],
                                summary_data['behavioral_measurables']['rewards'], summary_data['behavioral_measurables']['running_speed'])).T
    X_labels = ['stimulus contrast', 'licking', 'rewards', 'running speed']


# -------------- REGIONAL REGRESSION --------------
run_regional_regression = True
if run_regional_regression:
    # Get fluorescence data into df/f format and matrix for regression
    n_time_steps = summary_data['ROIs_F'][summary_data['ROIs_F'].keys()[0]].size
    n_regions = len(summary_data['ROIs_F'].keys())
    region_data = np.zeros((n_time_steps, n_regions))
    region_labels = []
    for i,key in enumerate(sorted(summary_data['ROIs_F'].keys())):
        region_data[:, i] = (summary_data['ROIs_F'][key] - summary_data['ROIs_F0'][key]) / summary_data['ROIs_F0'][key]
        region_labels.append(key)

    # load pairs to exclude - want to run recurrent regression without using paired left/right region
    excludePairs = np.load(basepath + 'regression/regions/excludePairs.npy')

    # Construct training and test sets
    region_data_train = {'Y': region_data[20000:183000, :], 'X': regressor_data[20000:183000, :], 'X_labels': X_labels, 'Y_labels': region_labels}
    region_data_test = {'Y': region_data[183000:-20000, :], 'X': regressor_data[183000:-20000, :], 'X_labels': X_labels, 'Y_labels': region_labels}
    pickle.dump(region_data_train, open(basepath + "regression/regions/train.pkl",'w'))
    pickle.dump(region_data_test, open(basepath + "regression/regions/test.pkl",'w'))

    # Run regular and recurrent regressions.
    # based on cross-correlations, convolve over 4 seconds
    lr1_regions = LinearRegression(use_design_matrix=True, convolution_length=400)
    lr1_regions.fit(region_data_train['Y'], region_data_train['X'])
    pickle.dump(lr1_regions, open(basepath + "regression/regions/results_nonrecurrent.pkl",'w'))
    lr2_pca = RecurrentRegression(use_design_matrix=True, convolution_length=400)
    lr2_pca.fit(region_data_train['Y'], region_data_train['X'])
    pickle.dump(lr2_pca, open(basepath + "regression/regions/results_recurrent.pkl", 'w'))


# -------------- PCA --------------
run_pca_regression = True
if run_pca_regression:
    # Load data
    tb_open = tb.open_file(image_data_path, 'r')
    image_data_train = tb_open.root.data[:,20000:183000].T
    image_data_test = tb_open.root.data[:,183000:-20000].T
    tb_open.close()

    pca = PCA(n_components=20)
    pca.fit(image_data_train)
    pickle.dump(pca, open(basepath + "regression/pca/pca.pkl",'w'))

    pca_data_train = {'Y': pca.transform(image_data_train), 'X': regressor_data[20000:183000, :], 'X_labels': X_labels}
    pca_data_test = {'Y': pca.transform(image_data_test), 'X': regressor_data[183000:-20000, :], 'X_labels': X_labels}
    pickle.dump(pca_data_train, open(basepath + "regression/pca/train.pkl",'w'))
    pickle.dump(pca_data_test, open(basepath + "regression/pca/test.pkl",'w'))

    lr1_pca = LinearRegression(use_design_matrix=True, convolution_length=400)
    lr1_pca.fit(pca_data_train['Y'], pca_data_train['X'])
    pickle.dump(lr1_pca, open(basepath + "regression/pca/results_nonrecurrent.pkl", 'w'))
    lr2_pca = RecurrentRegression(use_design_matrix=True, convolution_length=400)
    lr2_pca.fit(pca_data_test['Y'], pca_data_test['X'])
    pickle.dump(lr2_pca, open(basepath + "regression/pca/results_recurrent.pkl", 'w'))


# -------------- Factor Analysis --------------
run_fa_regression = True
if run_fa_regression:
    if not run_pca_regression:
        # Load data
        tb_open = tb.open_file(image_data_path, 'r')
        image_data_train = tb_open.root.data[:,20000:183000].T
        image_data_test = tb_open.root.data[:,183000:-20000].T
        tb_open.close()

    fa = FactorAnalysis(n_components=20)
    fa.fit(image_data_train)
    pickle.dump(fa, open(basepath + "regression/fa/fa.pkl",'w'))

    fa_data_train = {'Y': fa.transform(image_data_train), 'X': regressor_data[20000:183000, :], 'X_labels': X_labels}
    fa_data_test = {'Y': fa.transform(image_data_test), 'X': regressor_data[183000:-20000, :], 'X_labels': X_labels}
    pickle.dump(fa_data_train, open(basepath + "regression/fa/train.pkl",'w'))
    pickle.dump(fa_data_test, open(basepath + "regression/fa/test.pkl",'w'))

    lr1_fa = LinearRegression(use_design_matrix=True, convolution_length=400)
    lr1_fa.fit(fa_data_train['Y'], fa_data_train['X'])
    pickle.dump(lr1_fa, open(basepath + "regression/fa/results_nonrecurrent.pkl", 'w'))
    lr2_fa = RecurrentRegression(use_design_matrix=True, convolution_length=400)
    lr2_fa.fit(fa_data_test['Y'], fa_data_test['X'])
    pickle.dump(lr2_fa, open(basepath + "regression/fa/results_recurrent.pkl", 'w'))
