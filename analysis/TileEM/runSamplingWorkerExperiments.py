from numpy import  *
from dataset import Dataset
from BB2tile import *
from greedy import *
from data import *
from experiment import *
import pandas as pd
import string
from tqdm import tqdm
import pickle as pkl
def run_experiment(tiles, objIndicatorMat,method="average"):
    if method=="average":
        T , L, g, solutionList = experiment_avg(objIndicatorMat)
    elif method=="median":
        T, L, g, solutionList = experiment_median(objIndicatorMat)
    elif method=="local":
        T, L, g, solutionList = experiment_local(1, objIndicatorMat)
    elif method=="exhaustive":
        T, L, g, solutionList = experiment_exhaustive(1,  objIndicatorMat,step_size=500)
        L = np.array(L)
        try:
        L  = L [L !=np.inf]
        maxidx = argmax(L )
        L  = L[maxidx] #Maximum likelihood
        T  = T[maxidx]
        except(ValueError):
            L  = np.inf
            T  =np.nan
    L = np.array(L)
    return T,L,np.array([gmat2arr(g)]),solutionList 

def gmat2arr(g):
    if g is None:
        return []
    else:
        return np.array(g.T)[0]
if __name__ == "__main__":
    img_info,object_tbl,bb_info,hit_info = load_info()
    Nsample = sys.argv[1]
    DIR_NAME = '{}_worker_output/'.format(Nsample)
    object_lst = list(object_tbl.id)
    Tfile = open(DIR_NAME+"Tarea.txt",'a')
    Lfile = open(DIR_NAME+"likelihood.txt",'a')
    for objid in tqdm(object_lst):
        print "Working on obj:",objid
        tiles, objIndicatorMat = createObjIndicatorMatrix(objid,PRINT=False)
        print "Saving checkpoint..."
        Tfile = open(DIR_NAME+"Tarea.txt",'a')
        Lfile = open(DIR_NAME+"likelihood.txt",'a')
        T,L,g,soln = run_all_experiments(tiles, objIndicatorMat)

        Tfile.write(T.__repr__().replace('(','').replace(')','\n'))
        Lfile.write(L.__repr__().replace('(','').replace(')','\n'))

        Tfile.close()
        Lfile.close()
        pkl.dump(g,open(DIR_NAME+"gfile{}.pkl".format(objid),'w'))
        pkl.dump(soln,open(DIR_NAME+"solnfile{}.pkl".format(objid),'w'))
        pkl.dump(tiles,open(DIR_NAME+"tiles{}.pkl".format(objid),'w'))
    Tfile.close()
    Lfile.close()
