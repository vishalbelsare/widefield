import numpy as np
from scipy.optimize import nnls
from sklearn.decomposition import NMF

class NMF:
    def __init__(self, n_components=None, sparsity=None, sparsity_penalty=1., regularization=None, regularization_penalty=1., max_iter=200):
        self.n_components = n_components
        self.sparsity = sparsity
        self.sparsity_penalty = sparsity_penalty
        self.regularization = regularization
        self.regularization_penalty = regularization_penalty
        self.max_iter = max_iter
        #raise NotImplementedError("NMF not implemented yet")

    def fit(self, Xin):
        # Fit X = W*H, implementing coordinate descent as in scikit-learn implementation
        n_samples, n_features = Xin.shape
        if self.n_components is None:
            self.n_components = min(n_samples, n_features)

        # Randomly initialize W and H
        avg = np.sqrt(Xin.mean() / self.n_components)
        H = avg * np.random.randn(n_features, self.n_components)
        W = avg * np.random.randn(n_samples, self.n_components)
        np.abs(H, H)
        np.abs(W, W)
        H /= np.sqrt(np.sum(H**2, axis=0))

        l1_H, l2_H, l1_W, l2_W = 0, 0, 0, 0
        if self.sparsity in ('both', 'components'):
            l1_H = self.sparsity_penalty
        if self.sparsity in ('both', 'transformation'):
            l1_W = self.sparsity_penalty
        if self.regularization in ('both', 'components'):
            l2_H = self.regularization_penalty
        if self.regularization in ('both', 'transformation'):
            l2_W = self.regularization_penalty

        objective = np.inf
        for i in range(self.max_iter):
            # ---------- UPDATE W ----------
            Wnew = np.empty(W.shape)
            for i in range(n_samples):
                Wnew[i] = nnls(np.concatenate((H, np.sqrt(l1_W)*np.ones((1,self.n_components)), np.sqrt(l2_W)*np.eye(self.n_components)),axis=0),
                     np.hstack((Xin[i], np.zeros(self.n_components+1))))[0]
            W = Wnew

            objective_new = np.sum((Xin - np.dot(W,H.T))**2) + l1_H*np.sum(np.abs(H)**2) + l1_W*np.sum(np.abs(W)**2) + l2_H*np.sum(H**2) + l2_W*np.sum(W**2)
            if objective_new > objective:
                print "warning: objective value increased"
            objective = objective_new

            # ---------- UPDATE H ----------
            Hnew = np.empty(H.shape)
            for i in range(n_features):
                Hnew[i] = nnls(np.concatenate((W, np.sqrt(l1_H)*np.ones((1,self.n_components)), np.sqrt(l2_H)*np.eye(self.n_components)),axis=0),
                     np.hstack((Xin[:,i], np.zeros(self.n_components+1))))[0]
            H = Hnew
            # normalize H
            H /= np.sqrt(np.sum(H**2, axis=0))

            objective_new = np.sum((Xin - np.dot(W,H.T))**2) + l1_H*np.sum(np.abs(H)**2) + l1_W*np.sum(np.abs(W)**2) + l2_H*np.sum(H**2) + l2_W*np.sum(W**2)
            if objective_new > objective:
                print "warning: objective value increased"
            objective = objective_new

        self.components = H
        return W


class SparseNMF:
    # Reference: "Sparse NMF, half-baked or well done?"
    def __init__(self, n_components=None, cf='KL', beta=1.0, sparsity_penalty=0.0, max_iter=200):
        self.n_components = n_components
        self.sparsity_penalty = sparsity_penalty
        self.max_iter = max_iter
        self.beta = beta
        self.flr = 1e-9

    def fit(self, X, h_ind=None, w_ind=None, display=False):
        n_samples, n_features = X.shape
        if self.n_components is None:
            self.n_components = min(n_samples, n_features)

        # initialize W and H
        W = np.random.rand(n_samples, self.n_components)
        H = np.random.rand(self.n_components, n_features)

        # sparsity per matrix entry - still figuring out what this means
        # if length(params.sparsity) == 1
        # params.sparsity = ones(r, n) * params.sparsity;
        # elseif size(params.sparsity, 2) == 1
        # params.sparsity = repmat(params.sparsity, 1, n);
        # end
        sparsity = np.ones((self.n_components, n_features))*self.sparsity_penalty

        # Normalize the columns of W and rescale H accordingly
        Wn = np.sqrt(np.sum(W**2,axis=0))
        W /= Wn
        H = (H.T*Wn).T

        lam = np.maximum(np.dot(W,H), self.flr)
        last_cost = np.inf

        obj_div = np.zeros(self.max_iter)
        obj_cost = np.zeros(self.max_iter)

        if h_ind is None:
            h_ind = np.ones(self.n_components, dtype=int)
        if w_ind is None:
            w_ind = np.ones(self.n_components, dtype=int)
        update_h = np.sum(h_ind)
        update_w = np.sum(w_ind)

        for i in range(self.max_iter):
            # H updates
            if update_h > 0:
                if self.beta == 1:
                    dph = (np.sum(W[:, h_ind], axis=0) + sparsity.T).T
                    dph = np.maximum(dph, self.flr)
                    dmh = np.dot(W[:, h_ind].T, (X / lam))
                    H[h_ind] = H[h_ind, :]*dmh/dph
                elif self.beta == 2:
                    dph = np.dot(W[:, h_ind].T, lam) + sparsity
                    dph = np.maximum(dph, self.flr)
                    dmh = np.dot(W[:, h_ind].T,X)
                    H[h_ind] = H[h_ind, :]* dmh / dph
                else:
                    dph = np.dot(W[:, h_ind].T, lam**(self.beta - 1.0)) + sparsity
                    dph = np.maximum(dph, self.flr)
                    dmh = np.dot(W[:, h_ind].T, (X * lam**(self.beta - 2.0)))
                    H[h_ind, :] = H[h_ind, :] * dmh / dph

                lam = np.maximum(np.dot(W,H), self.flr)

            # W updates
            if update_w > 0:
                if self.beta == 1:
                    dpw = np.sum(H[w_ind, :], axis=1).T + np.sum(np.dot((X / lam), H[w_ind, :].T) * W[:, w_ind], axis=0)*W[:, w_ind]
                    dpw = np.maximum(dpw, self.flr)
                    dmw = np.dot(X/lam, H[w_ind, :].T) + np.sum(np.sum(H[w_ind, :],axis=1).T*W[:, w_ind],axis=0)*W[:, w_ind]
                    W[:, w_ind] = W[:,w_ind] * dmw / dpw
                elif self.beta == 2:
                    dpw = np.dot(lam, H[w_ind, :].T) + np.sum(np.dot(X, H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                    dpw = np.maximum(dpw, self.flr)
                    dmw = np.dot(X, H[w_ind, :].T) + np.sum(np.dot(lam, H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                    W[:, w_ind] = W[:,w_ind] * dmw / dpw
                else:
                    dpw = np.dot(lam**(self.beta - 1.),H[w_ind, :].T) + np.sum(np.dot(X * lam**(self.beta - 2.), H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                    dpw = np.maximum(dpw, self.flr)
                    dmw = np.dot(X * lam**(self.beta - 2.), H[w_ind, :].T) + np.sum(np.dot(lam**(self.beta - 1.), H[w_ind, :].T) * W[:, w_ind], axis=0)*W[:, w_ind]
                    W[:, w_ind] = W[:,w_ind] * dmw / dpw

                # Normalize the columns of W
                W = W/np.sqrt(np.sum(W**2,axis=0))
                lam = np.maximum(np.dot(W,H), self.flr)

            # Compute the objective function
            if self.beta == 1:
                div = np.sum(X * np.log(X / lam) - X + lam)
            elif self.beta == 2:
                div = np.sum((X - lam)**2)
            elif self.beta == 0:
                div = np.sum(X / lam - np.log( X / lam) - 1.)
            else:
                div = np.sum(X**self.beta + (self.beta - 1.)*lam**self.beta - self.beta * X * lam**(self.beta - 1.)) / (self.beta * (self.beta - 1.))
            cost = div + np.sum(sparsity * H)

            obj_div[i] = div
            obj_cost[i] = cost

            if display:
                print "iteration %d div = %.3e cost = %.3e\n" % (i, div, cost)

            # Convergence check
            if i > 1:
                e = np.abs(cost - last_cost) / last_cost
            if cost >= last_cost:
                print "cost increased on iteration %d" % i

            last_cost = cost

        self.components = H
        return W

    def infer_latent(self, X, w_ind=None):
        n_samples, n_features = X.shape
        W = np.random.rand(n_samples, self.n_components)
        W /= np.sqrt(np.sum(W**2,axis=0))
        H = self.components
        lam = np.maximum(np.dot(W,H), self.flr)

        if w_ind is None:
            w_ind = np.ones(self.n_components, dtype=int)

        for i in range(self.max_iter):
            if self.beta == 1:
                dpw = np.sum(H[w_ind, :], axis=1).T + np.sum(np.dot((X / lam), H[w_ind, :].T) * W[:, w_ind], axis=0)*W[:, w_ind]
                dpw = np.maximum(dpw, self.flr)
                dmw = np.dot(X/lam, H[w_ind, :].T) + np.sum(np.sum(H[w_ind, :],axis=1).T*W[:, w_ind],axis=0)*W[:, w_ind]
                W[:, w_ind] = W[:,w_ind] * dmw / dpw
            elif self.beta == 2:
                dpw = np.dot(lam, H[w_ind, :].T) + np.sum(np.dot(X, H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                dpw = np.maximum(dpw, self.flr)
                dmw = np.dot(X, H[w_ind, :].T) + np.sum(np.dot(lam, H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                W[:, w_ind] = W[:,w_ind] * dmw / dpw
            else:
                dpw = np.dot(lam**(self.beta - 1.),H[w_ind, :].T) + np.sum(np.dot(X * lam**(self.beta - 2.), H[w_ind, :].T) * W[:, w_ind],axis=0)*W[:, w_ind]
                dpw = np.maximum(dpw, self.flr)
                dmw = np.dot(X * lam**(self.beta - 2.), H[w_ind, :].T) + np.sum(np.dot(lam**(self.beta - 1.), H[w_ind, :].T) * W[:, w_ind], axis=0)*W[:, w_ind]
                W[:, w_ind] = W[:,w_ind] * dmw / dpw

            W /= np.sqrt(np.sum(W**2,axis=0))
            lam = np.maximum(np.dot(W,H), self.flr)

        return W

    def reconstruct(self, X, W=None):
        if W is None:
            W = self.infer_latent(X)
        return np.dot(W, self.components)