# Run the PR calculation for TileEM on various thresholds based on  the adjacency and the non-adjacency ML construction
# Creates a Tile_PR.csv in each of the base_dir/dir_name directory 
import pandas as pd 
import pickle as pkl 
from qualityBaseline import * 
from calc_Tstar import * 
import os 
import time 
base_dir= "stored_ptk_run"
PR_non_adjacency = pd.read_csv("COMPILED_PR_nadj.csv")
start = time.time()
worker_Nbatches={5:10,10:8,15:6,20:4,25:2,30:1}
sampleN_lst=worker_Nbatches.keys()
from TileEM_plot_toolbox import *
def majority_vote(objid,heuristic="50%"):
    #Compute PR for majority voted region
    tiles = pkl.load(open("vtiles{}.pkl".format(objid)))
    indMat = pkl.load(open("indMat{}.pkl".format(objid)))
    workers = pkl.load(open("worker{}.pkl".format(objid)))

    area = indMat[-1]
    votes = indMat[:-1].sum(axis=0)
    if heuristic=="50%":
        tidx=np.where(votes>np.shape(indMat[:-1])[0]/2.)[0]
    elif heuristic=="topk":
        topk=10
        tidx = np.argsort(votes)[::-1][:topk]
    elif heuristic=="topPercentile":
        percentile=95
        tidx=np.where(votes>np.percentile(votes,percentile))[0]
    P,R = compute_PR(objid,tidx,tiles)
    if len(tidx)==0:
        P=0
        R=0
    return P,R
start = time.time()
for Nworker in sampleN_lst:
    for batch_num in range(worker_Nbatches[Nworker]):
        dir_name = "{0}worker_rand{1}".format(Nworker,batch_num)
        print "Working on :", dir_name
        os.chdir(base_dir+"/"+dir_name)
        #Tile
        tbl=[]
        col_lst = []
        tmp_tbl=[]
        for i,fname in enumerate(glob("obj*")):
            objid=int(fname[3:])
            BBG =get_gt(objid)
            tmp_tbl=[objid]
            if i==0: col_lst = ["object_id"]
            tiles = pkl.load(open("vtiles{}.pkl".format(objid)))
            for thresh in [-40,-20,0,20,40]:
                try:
                    Tstar_idx_lst = list(set(pkl.load(open("obj{0}/thresh{1}/iter_5/tid_list.pkl".format(objid,thresh)))))
                    print "Working on obj{0}/thresh{1}/".format(objid,thresh)
                    #TileEMP,TileEMR = compute_PR(objid,np.array(Tstar_lst),tiles)
                    # Tile EM with adjacency
                    Tstar_lst = [tiles[tidx] for tidx in Tstar_idx_lst]
                    TileEMP = precision_from_list(Tstar_lst,BBG)
                    TileEMR = recall_from_list(Tstar_lst,BBG)
                    # Tile EM without adjacency
                    selected_PR = PR_non_adjacency[(PR_non_adjacency["num_workers"]==Nworker)&(PR_non_adjacency["sample_num"]==batch_num)&\
                                     (PR_non_adjacency["objid"]==objid)&(PR_non_adjacency["iter_num"]==5)&\
                                     (PR_non_adjacency["thresh"]==thresh)]
                    TileEMP_NA = float(selected_PR["precision"])
                    TileEMR_NA = float(selected_PR["recall"])
		    # Pixel EM 
		    PR_pixelEM = pd.read_csv("pixel_em/full_PR_table.csv")
		    PR_pixelEMi =PR_pixelEM[(PR_pixelEM["num_workers"]==Nworker)&(PR_pixelEM["sample_num"]==batch_num)&\
					(PR_pixelEM["objid"]==objid)&(PR_pixelEM["thresh"]==thresh)]
		    PixelEMP= float(PR_pixelEMi["EM_precision"]) 
		    PixelEMR= float(PR_pixelEMi["EM_recall"])
                    tmp_tbl.extend([TileEMP,TileEMR,TileEMP_NA,TileEMR_NA,PixelEMP,PixelEMR])
                    if i==0: 
                        col_lst.extend(["P [TileEM thres={}]".format(thresh),"R [TileEM thres={}]".format(thresh),\
                                    "P [TileEM NA thres={}]".format(thresh),"R [TileEM NA thres={}]".format(thresh)])
                except(IOError):
                    print "No file exist: obj{0}/thresh{1}/iter_5/tid_list.pkl".format(objid,thresh)
                    pass
            # Majority Vote
            PMVT,RMVT = majority_vote(objid,heuristic="50%")
            PMVTtopk,RMVTtopk = majority_vote(objid,heuristic="topk")
            PMVTtopP,RMVTtopP = majority_vote(objid,heuristic="topPercentile")
            tmp_tbl.extend([PMVT,RMVT,PMVTtopk,RMVTtopk,PMVTtopP,RMVTtopP])
            if i==0: col_lst.extend(["P [MVT]","R [MVT]","P [MVTtop10]","R [MVTtop10]","P [MVTtop95%]","R [MVTtop95%]"])
            tbl.append(tmp_tbl) #[objid,TileEMP,TileEMR,PMVT,RMVT,PMVTtopk,RMVTtopk,PMVTtopP,RMVTtopP]
        Tile_df = pd.DataFrame(tbl,columns=col_lst)
        Tile_df.to_csv("Tile_PR.csv")
        os.chdir("../../")
end = time.time()
print "Time Elapsed: ", end-start 