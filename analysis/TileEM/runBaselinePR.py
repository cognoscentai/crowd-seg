# Compute PR from all baselines + TileEM
import pickle as pkl 
from TileEM_plot_toolbox import *
from qualityBaseline import *
from glob import glob
from collections import OrderedDict
from problematic_vtiles import * 
df = pd.read_csv("../computed_my_COCO_BBvals.csv",index_col=0)
worker_Nbatches={5:10,10:8,15:6,20:4,25:2,30:1}
sampleN_lst=worker_Nbatches.keys()
mode="aggregate_sample_table"
if mode =="recompute_sample_batch_table":
	# Compute and save a  PR_tbl_all.csv into each sample_batch folder 
	for Nworker in sampleN_lst:
		for batch_num in range(worker_Nbatches[Nworker]):
			dir_name = "{0}worker_rand{1}".format(Nworker,batch_num)
			
			print "Working on :", dir_name
			os.chdir("sample/"+dir_name)
			 
			# Creating 2 empty precision recall table containing P,R for each metric used 
			cols = [u'Num Points',u'Area Ratio',u'Jaccard [Self]', u'Precision [Self]', u'Recall [Self]']

			PR_tbl = pd.DataFrame()#index=object_lst)#,columns=cols)
			PR_tbl["object_id"]=object_lst
			# Summarization-Based Method
			df.ix[df["Precision [Self]"]>1,"Precision [Self]"]=1
			df.ix[df["Recall [Self]"]>1,"Recall [Self]"]=1
			df = df[~(df["worker_id"].isin([1,2,3]))] #Filter our ground truth workers
			for attr in cols:
				tbl=[]
				for objid in object_lst:
					workers=pkl.load(open("worker{}.pkl".format(objid)))
					filtered_df = df[(df["worker_id"].isin(workers))&(df["object_id"]==objid)] #only look at summarization scores of sampled workers
					best_worker_BB = filtered_df[filtered_df[attr]==filtered_df[attr].max()]
					tbl.append([objid,best_worker_BB["Precision [Self]"].values[0],best_worker_BB["Recall [Self]"].values[0]])
				tmp_PR_tbl = pd.DataFrame(tbl,columns=["object_id","Precision","Recall"])
				PR_tbl["P [{}]".format(attr)]=tmp_PR_tbl["Precision"]
				PR_tbl["R [{}]".format(attr)]=tmp_PR_tbl["Recall"]
			# Vision based methods 
			for threshold in [10,50,90]:
				visionPR = pd.read_csv("../../../PR{}.csv".format(threshold))
				PR_tbl["P [Vision{}%]".format(threshold)] = visionPR["precision"]
				PR_tbl["R [Vision{}%]".format(threshold)] = visionPR["recall"]
			#MVT, Tile
			tbl=[]
			for fname in glob("Tstar_idx_obj*.pkl"):
				objid=int(fname.split("_")[-1].split(".")[0][3:])
				tiles = pkl.load(open("vtiles{}.pkl".format(objid)))
				#Tile EM
				Tstar_lst = pkl.load(open("Tstar_idx_obj{}.pkl".format(objid)))
				TileEMP,TileEMR=compute_PR(objid,np.array(Tstar_lst[-1]),tiles)
				# Majority Vote 
				PMVT,RMVT = majority_vote(objid,heuristic="50%")
				PMVTtopk,RMVTtopk = majority_vote(objid,heuristic="topk")
				PMVTtopP,RMVTtopP = majority_vote(objid,heuristic="topPercentile")
				tbl.append([objid,TileEMP,TileEMR,PMVT,RMVT,PMVTtopk,RMVTtopk,PMVTtopP,RMVTtopP])
			Tile_df = pd.DataFrame(tbl,columns=["object_id","P [TileEM]","R [TileEM]","P [MVT]","R [MVT]","P [MVTtop10]","R [MVTtop10]","P [MVTtop95%]","R [MVTtop95%]"])
			PR_tbl_all = PR_tbl.merge(Tile_df,on="object_id")
			#Save to file in that folder 
			PR_tbl_all.to_csv("PR_tbl_all.csv")
			os.chdir("../..")
elif mode =="aggregate_sample_table" :
    sampleN_lst=sorted(worker_Nbatches.keys())

    for Nworker in sampleN_lst:
        print "Working on worker = ",Nworker
        batch_all_data=[]
        for batch_num in range(worker_Nbatches[Nworker]):
            dir_name = "sample/{0}worker_rand{1}".format(Nworker,batch_num)
            batch_i_data=pd.read_csv(dir_name+"/PR_tbl_all.csv",index_col=0)
            #Drop the object rows where the objects have bad vtiles to begin with 
            bad_vtile_objs = list(problematic[(problematic["Nworker"]==Nworker)&(problematic["batch_num"]==batch_num)].objid)
            batch_i_data=batch_i_data.drop(bad_vtile_objs,errors='ignore')
            #batch_i_data[~batch_i_data["object_id"].isin(bad_vtile_objs)]
            # First set the object_id column the index, then reindex based on this index to correspond to object lst
            # This fills in a row of NaN for the missing data objects, so it normalizes the shape of our data table 
            batch_i_data = batch_i_data.set_index('object_id').reindex(object_lst,fill_value =0)
             # Add a row of non-nan count for averaging 
            nan_rowidx= list(batch_i_data[batch_i_data["P [Num Points]"]==0].index)
            non_nan_count = np.ones_like(object_lst)
            for row in nan_rowidx: non_nan_count[row-1]=0
            batch_i_data["non_nan_count"]=non_nan_count
            if batch_num==0:
                batch_all_data=batch_i_data
            else:
                batch_all_data+=batch_i_data
        try:
            batch_all_data=batch_all_data[batch_all_data.keys()[:-1]].divide(batch_all_data["non_nan_count"],axis=0)
            batch_all_data[batch_all_data>1]=1
            batch_all_data[batch_all_data<0]=0
	    print "Created sample{}_PR.csv".format(Nworker)
            batch_all_data.to_csv("sample{}_PR.csv".format(Nworker))
        except(ZeroDivisionError):
            print "No data for worker=",Nworker 