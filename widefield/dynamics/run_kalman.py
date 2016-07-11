import pickle
import numpy as np
import scipy.linalg as la
import tables as tb
from widefield.dynamics.lds import lds_model

mouseId = 'm187201'
collectionDate = '150727'
basepath = "/suppscr/riekesheabrown/kpchamp/data/"
datapath = basepath + mouseId + "/" + collectionDate + "/data_detrend_mask.h5"
f=tb.open_file(datapath,'r')
X=f.root.data[:,:]
f.close()

# note: total frames are 347973
Tmax, n_features = X.shape
# actually use only first 347904 = 128*2718 frames (for full would be 366000 = 128*2859)
Tmax = 347904
Twin = Tmax/8

lds = lds_model(X[0:10000,:].T, 300)
U, _, _ = la.svd(X[0:10000,:].T, full_matrices=False)
lds.C = U[:,0:300]
print >>open('progress.txt','a'), "SVD dims %d,%d" % lds.C.shape
lds.fit_em(X[0:10000,:].T, max_iters=10)   # do only one iteration of EM for timing purposes
#lds.fit_constrained(X[0:100,:].T)
pickle.dump(lds, open('/suppscr/riekesheabrown/kpchamp/lds_model_startSVD.pkl','w'))