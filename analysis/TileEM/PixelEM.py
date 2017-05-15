import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
from PIL import Image, ImageDraw
import sys
#sys.path.append("..")
from analysis_toolbox import *
#from poly_utils import *
import pickle
import json
# import math
import time
import os
BASE_DIR = '/home/jlee782/crowd-seg/analysis/TileEM/'
PIXEL_EM_DIR = BASE_DIR + 'pixel_em/'
ORIGINAL_IMG_DIR = '../../web-app/app/static/' 
from sample_worker_seeds import sample_specs 

def create_all_gt_and_worker_masks(objid, PLOT=False, PRINT=False, EXCLUDE_BBG=True):
    img_info, object_tbl, bb_info, hit_info = load_info()
    print objid
    # Ji_tbl (bb_info) is the set of all workers that annotated object i
    bb_objects = bb_info[bb_info["object_id"] == objid]
    if EXCLUDE_BBG:
        bb_objects = bb_objects[bb_objects.worker_id != 3]

    # Create a masked image for the object
    # where each of the worker BB is considered a mask and overlaid on top of each other
    img_name = img_info[img_info.id == int(object_tbl[object_tbl.id == objid]["image_id"])]["filename"].iloc[0]
    fname = ORIGINAL_IMG_DIR + img_name + ".png"
    img = mpimg.imread(fname)
    width, height = get_size(fname)

    outdir = '{}obj{}/'.format(PIXEL_EM_DIR, objid)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    obj_x_locs = [process_raw_locs([x, y])[0] for x, y in zip(bb_objects["x_locs"], bb_objects["y_locs"])]
    obj_y_locs = [process_raw_locs([x, y])[1] for x, y in zip(bb_objects["x_locs"], bb_objects["y_locs"])]
    worker_ids = list(bb_objects["worker_id"])

    # for x_locs, y_locs in zip(obj_x_locs, obj_y_locs):
    for i in range(len(obj_x_locs)):
        x_locs = obj_x_locs[i]
        y_locs = obj_y_locs[i]
        wid = worker_ids[i]

        img = Image.new('L', (width, height), 0)
        ImageDraw.Draw(img).polygon(zip(x_locs, y_locs), outline=1, fill=1)
        mask = np.array(img) == 1
        # plt.imshow(mask)
        with open('{}mask{}.pkl'.format(outdir, wid), 'w') as fp:
            fp.write(pickle.dumps(mask))

        if PLOT:
            plt.figure()
            plt.imshow(mask, interpolation="none")  # ,cmap="rainbow")
            plt.colorbar()
            plt.show()

    my_BB = pd.read_csv('{}my_ground_truth.csv'.format(BASE_DIR))
    bb_match = my_BB[my_BB.object_id == objid]
    x_locs, y_locs = process_raw_locs([bb_match['x_locs'].iloc[0], bb_match['y_locs'].iloc[0]])
    img = Image.new('L', (width, height), 0)
    ImageDraw.Draw(img).polygon(zip(x_locs, y_locs), outline=1, fill=1)
    mask = np.array(img) == 1
    with open('{}gt.pkl'.format(outdir), 'w') as fp:
        fp.write(pickle.dumps(mask))


def get_worker_mask(objid, worker_id):
    indir = '{}obj{}/'.format(PIXEL_EM_DIR, objid)
    return pickle.load(open('{}mask{}.pkl'.format(indir, worker_id)))


def get_gt_mask(objid):
    indir = '{}obj{}/'.format(PIXEL_EM_DIR, objid)
    return pickle.load(open('{}gt.pkl'.format(indir)))


def create_mega_mask(objid, PLOT=False, sample_name='5workers_rand0', PRINT=False, EXCLUDE_BBG=True):
    img_info, object_tbl, bb_info, hit_info = load_info()
    # Ji_tbl (bb_info) is the set of all workers that annotated object i
    bb_objects = bb_info[bb_info["object_id"] == objid]
    if EXCLUDE_BBG:
        bb_objects = bb_objects[bb_objects.worker_id != 3]
    # Sampling Data from Ji table
    sampleNworkers = sample_specs[sample_name][0]
    if sampleNworkers > 0 and sampleNworkers < len(bb_objects):
        bb_objects = bb_objects.sample(n=sample_specs[sample_name][0], random_state=sample_specs[sample_name][1])

    img_name = img_info[img_info.id == int(object_tbl[object_tbl.id == objid]["image_id"])]["filename"].iloc[0]
    fname = ORIGINAL_IMG_DIR + img_name + ".png"
    width, height = get_size(fname)
    mega_mask = np.zeros((height, width))

    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    worker_ids = list(bb_objects["worker_id"])
    with open('{}worker_ids.json'.format(outdir), 'w') as fp:
        fp.write(json.dumps(worker_ids))

    for wid in worker_ids:
        mask = get_worker_mask(objid, wid)
        mega_mask += mask

    if PLOT:
        # Visualize mega_mask
        plt.figure()
        plt.imshow(mega_mask, interpolation="none")  # ,cmap="rainbow")
        # plt.imshow(mask, interpolation="none")  # ,cmap="rainbow")
        plt.colorbar()
        plt.savefig('{}mega_mask.png'.format(outdir))

    # TODO: materialize masks
    with open('{}mega_mask.pkl'.format(outdir), 'w') as fp:
        fp.write(pickle.dumps(mega_mask))


def get_mega_mask(sample_name, objid):
    indir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    return pickle.load(open('{}mega_mask.pkl'.format(indir)))


def workers_in_sample(sample_name, objid):
    indir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    return json.load(open('{}worker_ids.json'.format(indir)))


def get_all_worker_mega_masks_for_sample(sample_name, objid):
    worker_masks = dict()  # key = worker_id, value = worker mask
    worker_ids = workers_in_sample(sample_name, objid)
    for wid in worker_ids:
        worker_masks[wid] = get_worker_mask(objid, wid)
    return worker_masks


def create_MV_mask(sample_name, objid, plot=True,mode=""):
    # worker_masks = get_all_worker_mega_masks_for_sample(sample_name, objid)
    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if mode=="":
    	num_workers = len(workers_in_sample(sample_name, objid))
    	mega_mask = get_mega_mask(sample_name, objid)
    	MV_mask = np.zeros((len(mega_mask), len(mega_mask[0])))
    	[xs, ys] = np.where(mega_mask > (num_workers / 2))
    	for i in range(len(xs)):
            MV_mask[xs[i]][ys[i]] = 1
    	#outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    	with open('{}MV_mask.pkl'.format(outdir), 'w') as fp:
            fp.write(pickle.dumps(MV_mask))
   
    	if plot:
            plt.figure()
            plt.imshow(MV_mask, interpolation="none")  # ,cmap="rainbow")
            plt.colorbar()
            plt.savefig('{}MV_mask.png'.format(outdir))
    elif mode=="compute_pr_only":
	MV_mask = pickle.load(open('{}MV_mask.pkl'.format(outdir)))
    [p, r, j ] = get_precision_recall_jaccard(MV_mask, get_gt_mask(objid))
    with open('{}MV_prj.json'.format(outdir), 'w') as fp:
        fp.write(json.dumps([p, r,j]))


def get_MV_mask(sample_name, objid):
    indir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    return pickle.load(open('{}MV_mask.pkl'.format(indir)))


def get_precision_recall_jaccard(test_mask, gt_mask):
    num_intersection = 0.0  # float(len(np.where(test_mask == gt_mask)[0]))
    num_test = 0.0  # float(len(np.where(test_mask == 1)[0]))
    num_gt = 0.0  # float(len(np.where(gt_mask == 1)[0]))
    for i in range(len(gt_mask)):
        for j in range(len(gt_mask[i])):
            if test_mask[i][j] == 1 and gt_mask[i][j] == 1:
                num_intersection += 1
                num_test += 1
                num_gt += 1
            elif test_mask[i][j] == 1:
                num_test += 1
            elif gt_mask[i][j] == 1:
                num_gt += 1
    #try:
    #	return (num_intersection / num_test), (num_intersection / num_gt),(num_intersection/(num_gt+num_test-num_intersection))
    #except(ZeroDivisionError):
    #	print num_intersection
    #	print num_test
    #	print num_gt
    if num_test!=0:
 	return (num_intersection / num_test), (num_intersection / num_gt),(num_intersection/(num_gt+num_test-num_intersection))
    else:
	return 0.,0.,0. 


def worker_prob_correct(mega_mask,w_mask, gt_mask,Nworkers,exclude_isovote=False):
    if exclude_isovote:
	num_agreement= len(np.where((mega_mask==0) | (mega_mask==Nworkers))) # no votes
    else:
	num_agreement = 0
    #print "Num agreement:", num_agreement
    qj = float( len(np.where(w_mask == gt_mask)[0])-num_agreement ) / (len(gt_mask[0]) * len(gt_mask)-num_agreement)
    return qj 

def GTworker_prob_correct(mega_mask,w_mask, gt_mask,Nworkers,exclude_isovote=False):
    if exclude_isovote:
	not_agreement= ~((mega_mask==0) |  (mega_mask==Nworkers))
 	#print "disagreement tiles:", len(np.where(not_agreement)[0])
	#print "total tiles:", np.shape(mega_mask),"=",np.shape(mega_mask)[0]*np.shape(mega_mask)[1]
	#plt.figure()
	#plt.imshow(not_agreement)
	#plt.savefig("not_agreement.png")
	#print os.getcwd()
    else:
	not_agreement=True
    gt_Ncorrect = len(np.where((gt_mask==1) & (w_mask==1)& not_agreement)[0])
    gt_total = len(np.where(gt_mask==1& not_agreement)[0])
    ngt_Ncorrect = len(np.where((gt_mask==0) & (w_mask==0)& not_agreement)[0])
    ngt_total = len(np.where(gt_mask==0& not_agreement)[0])
    qp = float(gt_Ncorrect)/float(gt_total)
    qn = float(ngt_Ncorrect)/float(ngt_total)
    return qp,qn


def GTLSAworker_prob_correct(w_mask, gt_mask,area_mask, A_thres,step_size=5):
    non_zero_total=True
    update_iter = 0
    #step_size = A_thres/100. #adaptive step_size
    print non_zero_total and A_thres>0 and  update_iter<5000
    print A_thres
    print area_mask.min()
    print area_mask.max()
    while (non_zero_total and A_thres>=0 and A_thres<= area_mask.max() and  update_iter<5000):
        large_mask = area_mask>=A_thres
        small_mask = area_mask<A_thres
        large_gt_Ncorrect = len(np.where((gt_mask==1) & (w_mask==1) &(large_mask==1))[0])
        large_gt_total = len(np.where((gt_mask==1) &(large_mask==1))[0])
        large_ngt_Ncorrect = len(np.where((gt_mask==0) & (w_mask==0)& (large_mask==1))[0])
        large_ngt_total = len(np.where((gt_mask==0) &(large_mask==1))[0])

        small_gt_Ncorrect = len(np.where((gt_mask==1) & (w_mask==1) &(small_mask==1))[0])
        small_gt_total = len(np.where((gt_mask==1) &(small_mask==1))[0])
        small_ngt_Ncorrect = len(np.where((gt_mask==0) & (w_mask==0)& (small_mask==1))[0])
        small_ngt_total = len(np.where((gt_mask==0) &(small_mask==1))[0])
        
	print small_ngt_total,small_gt_total,large_ngt_total,large_gt_total 
	if small_ngt_total ==0 or small_gt_total==0: 
	    A_thres +=step_size
	    print "Increased A_thres:", A_thres
	elif large_ngt_total ==0 or large_gt_total==0:
	    A_thres -=step_size
 	    step_size = A_thres/100. #adaptive step_size
	    print "Decreased A_thres:", A_thres
	elif  large_ngt_total!=0 or large_gt_total!=0 or  small_ngt_total!=0 or small_gt_total!=0:
	    #Everything is non-zero
	    non_zero_total=False
        update_iter+=1
    print small_ngt_total,small_gt_total,large_ngt_total,large_gt_total
    qp1 = float(large_gt_Ncorrect)/float(large_gt_total) if large_gt_total!=0 else 0.6
    qn1 = float(large_ngt_Ncorrect)/float(large_ngt_total) if large_ngt_total!=0 else 0.6
    qp2 = float(small_gt_Ncorrect)/float(small_gt_total) if small_gt_total!=0 else 0.6
    qn2 = float(small_ngt_Ncorrect)/float(small_ngt_total) if small_ngt_total!=0 else 0.6
    #print "qp1,qn1,qp2,qn2:",qp1,qn1,qp2,qn2
    return qp1,qn1,qp2,qn2

def mask_log_probabilities(worker_masks, worker_qualities):
    worker_ids = worker_qualities.keys()
    log_probability_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))
    log_probability_not_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))

    for i in range(len(worker_masks[worker_ids[0]])):
        for j in range(len(worker_masks[worker_ids[0]][0])):
            for wid in worker_ids:
                log_probability_in_mask[i][j] += np.log(
                    worker_qualities[wid] if worker_masks[wid][i][j] == 1
                    else (1.0 - worker_qualities[wid])
                )
                log_probability_not_in_mask[i][j] += np.log(
                    (1.0 - worker_qualities[wid]) if worker_masks[wid][i][j] == 1
                    else worker_qualities[wid]
                )
    return log_probability_in_mask, log_probability_not_in_mask
def GTLSAmask_log_probabilities(worker_masks, qp1,qn1,qp2,qn2,area_mask,A_thres):
    worker_ids = qp1.keys()
    log_probability_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))
    log_probability_not_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))

    for i in range(len(worker_masks[worker_ids[0]])):
        for j in range(len(worker_masks[worker_ids[0]][0])):
            for wid in worker_ids:
                qp1i = qp1[wid]
                qn1i = qn1[wid]
                qp2i = qp2[wid]
                qn2i = qn2[wid]
                ljk = worker_masks[wid][i][j]
		large = area_mask[i][j]>=A_thres
		if large: 
                    if ljk==1:
                        log_probability_in_mask[i][j] += np.log(qp1i)
                        log_probability_not_in_mask[i][j] += np.log(1-qn1i)
                    else:
                        log_probability_not_in_mask[i][j] += np.log(qn1i)
                        log_probability_in_mask[i][j] += np.log(1-qp1i)
		else:
		    if ljk==1:
                        log_probability_in_mask[i][j] += np.log(qp2i)
                        log_probability_not_in_mask[i][j] += np.log(1-qn2i)
                    else:
                        log_probability_not_in_mask[i][j] += np.log(qn2i)
                        log_probability_in_mask[i][j] += np.log(1-qp2i) 
    return log_probability_in_mask, log_probability_not_in_mask

def GTmask_log_probabilities(worker_masks, qp,qn):
    worker_ids = qp.keys()
    log_probability_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))
    log_probability_not_in_mask = np.zeros((
        len(worker_masks[worker_ids[0]]), len(worker_masks[worker_ids[0]][0])
    ))

    for i in range(len(worker_masks[worker_ids[0]])):
        for j in range(len(worker_masks[worker_ids[0]][0])):
            for wid in worker_ids:
                qpi = qp[wid]
                qni = qn[wid]
                ljk = worker_masks[wid][i][j]
                # tjkInT = gt_mask[i][j]
                if ljk==1 :
                    log_probability_in_mask[i][j] += np.log(qpi)
                    log_probability_not_in_mask[i][j] += np.log(1-qni)
                else:
                    log_probability_not_in_mask[i][j] += np.log(qni)
                    log_probability_in_mask[i][j] += np.log(1-qpi)
    return log_probability_in_mask, log_probability_not_in_mask
def estimate_gt_from(log_probability_in_mask, log_probability_not_in_mask,thresh=0):
    gt_est_mask = np.zeros((len(log_probability_in_mask), len(log_probability_in_mask[0])))

    passing_xs, passing_ys = np.where(log_probability_in_mask >= thresh + log_probability_not_in_mask)
    for i in range(len(passing_xs)):
        gt_est_mask[passing_xs[i]][passing_ys[i]] = 1

    return gt_est_mask
def compute_A_thres(condition,area_mask):
    # Compute the new area threshold based on the meidan area of high confidence  pixels
    high_confidence_pixel_area = []
    #print np.where(pInT >= pNotInT)
    passing_xs, passing_ys = np.where(condition)#pInT >= pNotInT)
    #print passing_xs,passing_ys
    for i in range(len(passing_xs)):
       high_confidence_pixel_area.append(area_mask[passing_xs[i]][passing_ys[i]])
    A_thres = np.median(high_confidence_pixel_area)
    return A_thres	
def do_GTLSA_EM_for(sample_name, objid, num_iterations=5,load_p_in_mask=False,thresh=0, rerun_existing=False):
    print "Doing GTLSA EM" 
    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if not rerun_existing: 
        if os.path.isfile('{}GTLSA_EM_prj_thresh{}.json'.format(outdir,thresh)) :
            print "Already ran GTLSA, Skipped"
            return

    # initialize MV mask
    gt_est_mask = get_MV_mask(sample_name, objid)
    # In the first step we use 50% MV for initializing T*, A thres is therefore the median area pixel based on votes and noVotes
    mega_mask = get_mega_mask(sample_name, objid)
    area_mask = pkl.load(open("{}/tarea_mask.pkl".format(outdir)))
    A_thres = compute_A_thres(gt_est_mask==1,area_mask)
    #print "Initial A_thres:", A_thres
    worker_masks = get_all_worker_mega_masks_for_sample(sample_name, objid)
    #area_mask = pkl.load(open("{}/tarea_mask.pkl".format(outdir))) 
    for it in range(num_iterations):
        qp1 = dict()
        qn1 = dict()
        qp2 = dict()
        qn2 = dict()
        for wid in worker_masks.keys():
            qp1[wid],qn1[wid],qp2[wid],qn2[wid] = GTLSAworker_prob_correct(worker_masks[wid], gt_est_mask,area_mask,A_thres)
        if load_p_in_mask:
            #print "loaded pInT" 
            log_probability_in_mask=pkl.load(open('{}GTLSA_p_in_mask_{}.pkl'.format(outdir, it)))
            log_probability_not_in_mask =pkl.load(open('{}GTLSA_p_not_in_mask_{}.pkl'.format(outdir, it)))    
        else: 
            #Compute pInMask and pNotInMask 
            log_probability_in_mask, log_probability_not_in_mask = GTLSAmask_log_probabilities(worker_masks,qp1,qn1,qp2,qn2,area_mask,A_thres)
        gt_est_mask = estimate_gt_from(log_probability_in_mask, log_probability_not_in_mask,thresh=thresh)
	# Compute the new area threshold based on the meidan area of high confidence  pixels 
        A_thres = compute_A_thres(log_probability_in_mask>=log_probability_not_in_mask,area_mask) 
        # Compute PR mask based on the EM estimate mask from every iteration
    	[p, r, j] = get_precision_recall_jaccard(gt_est_mask, get_gt_mask(objid))
    	with open('{}GTLSA_EM_prj_iter{}_thresh{}.json'.format(outdir,it,thresh), 'w') as fp:
            fp.write(json.dumps([p, r, j]))
	
    #with open('{}GTLSA_p_in_mask_{}.pkl'.format(outdir, it), 'w') as fp:
    #    fp.write(pickle.dumps(log_probability_in_mask))
    #with open('{}GTLSA_p_not_in_mask_{}.pkl'.format(outdir, it), 'w') as fp:
    #    fp.write(pickle.dumps(log_probability_not_in_mask))
    with open('{}GTLSA_gt_est_mask_{}_thresh{}.pkl'.format(outdir, it,thresh), 'w') as fp:
        fp.write(pickle.dumps(gt_est_mask))
    #with open('{}GT_p_in_mask_{}.pkl'.format(outdir, it), 'w') as fp:
    #    fp.write(pickle.dumps(log_probability_in_mask))
    #with open('{}GT_p_not_in_mask_{}.pkl'.format(outdir, it), 'w') as fp:
    #    fp.write(pickle.dumps(log_probability_not_in_mask))
    #pickle.dump(qp1,open('{}GTLSA_qp1_{}_thresh{}.pkl'.format(outdir, it,thresh), 'w'))
    #pickle.dump(qn1,open('{}GTLSA_qn1_{}_thresh{}.pkl'.format(outdir, it,thresh), 'w'))
    #pickle.dump(qp2,open('{}GTLSA_qp2_{}_thresh{}.pkl'.format(outdir, it,thresh), 'w'))
    #pickle.dump(qn2,open('{}GTLSA_qn2_{}_thresh{}.pkl'.format(outdir, it,thresh), 'w'))
    
    plt.figure()
    plt.imshow(gt_est_mask, interpolation="none")  # ,cmap="rainbow")
    plt.colorbar()
    plt.savefig('{}GTLSA_EM_mask_thresh{}.png'.format(outdir,thresh))

def do_GT_EM_for(sample_name, objid, num_iterations=5,load_p_in_mask=False,thresh=0,rerun_existing=False,exclude_isovote=False,compute_PR_every_iter=False):
    print "Doing GT EM"
    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if rerun_existing:
        if os.path.isfile('{}GT_EM_prj_iter4_thresh{}.json'.format(outdir,thresh)):
            print "Already ran GT, Skipped"
            return
    if exclude_isovote: 
        mode ='iso'
    else:
        mode =''
    # initialize MV mask
    gt_est_mask = get_MV_mask(sample_name, objid)
    worker_masks = get_all_worker_mega_masks_for_sample(sample_name, objid)
    Nworkers=len(worker_masks)
    mega_mask = get_mega_mask(sample_name, objid)
    for it in range(num_iterations):
        print "Iteration #",it
        qp = dict()
        qn = dict()
        for wid in worker_masks.keys():
            qp[wid],qn[wid] = GTworker_prob_correct(mega_mask,worker_masks[wid], gt_est_mask,Nworkers,exclude_isovote=exclude_isovote)
        if load_p_in_mask:
            #print "loaded pInT" 
            log_probability_in_mask=pkl.load(open('{}{}GT_p_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh)))
            log_probability_not_in_mask =pkl.load(open('{}{}GT_p_not_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh)))    
        else: 
            #Compute pInMask and pNotInMask 
            log_probability_in_mask, log_probability_not_in_mask = GTmask_log_probabilities(worker_masks,qp,qn)
        gt_est_mask = estimate_gt_from(log_probability_in_mask, log_probability_not_in_mask,thresh=thresh)
        if compute_PR_every_iter:
            # Compute PR mask based on the EM estimate mask from every iteration
            [ p, r, j] = get_precision_recall_jaccard(gt_est_mask, get_gt_mask(objid))
            with open('{}{}GT_EM_prj_iter{}_thresh{}.json'.format(outdir,mode,it,thresh), 'w') as fp:
                fp.write(json.dumps([p, r, j]))
	    # Save only during the last iteration 
	    with open('{}{}GT_gt_est_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh), 'w') as fp:
		fp.write(pickle.dumps(gt_est_mask))
	    pickle.dump(log_probability_in_mask,open('{}{}GT_p_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh),'w'))
 	    pickle.dump(log_probability_not_in_mask,open('{}{}GT_p_not_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh),'w'))
	    pickle.dump(qp,open('{}{}GT_qp_{}_thresh{}.pkl'.format(outdir, mode,it,thresh), 'w'))
	    pickle.dump(qn,open('{}{}GT_qn_{}_thresh{}.pkl'.format(outdir, mode,it,thresh), 'w'))
    if not compute_PR_every_iter:
        # Compute PR mask based on the EM estimate mask from the last iteration
        [p, r, j] = get_precision_recall_jaccard(gt_est_mask, get_gt_mask(objid))
        with open('{}{}GT_EM_prj_thresh{}.json'.format(outdir,mode,thresh), 'w') as fp:
            fp.write(json.dumps([p, r, j]))
    plt.figure()
    plt.imshow(gt_est_mask, interpolation="none")  # ,cmap="rainbow")
    plt.colorbar()
    plt.savefig('{}{}GT_EM_mask_thresh{}.png'.format(outdir,mode,thresh))
def GroundTruth_doM_once(sample_name, objid, num_iterations=5,load_p_in_mask=False,thresh=0,rerun_existing=False,exclude_isovote=False,compute_PR_every_iter=False):
    print "Doing GroundTruth_doM_once"
    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if exclude_isovote:
        mode ='iso'
    else:
        mode =''
    # initialize MV mask
    gt_est_mask = get_gt_mask(objid)
    worker_masks = get_all_worker_mega_masks_for_sample(sample_name, objid)
    Nworkers= len(worker_masks)
    mega_mask = get_mega_mask(sample_name, objid)
    qp = dict()
    qn = dict()
    for wid in worker_masks.keys():
        qp[wid],qn[wid] = GTworker_prob_correct(mega_mask,worker_masks[wid], gt_est_mask,Nworkers,exclude_isovote=exclude_isovote)
    #Compute pInMask and pNotInMask
    log_probability_in_mask, log_probability_not_in_mask = GTmask_log_probabilities(worker_masks,qp,qn)
    gt_est_mask = estimate_gt_from(log_probability_in_mask, log_probability_not_in_mask,thresh=thresh)
    pickle.dump(log_probability_in_mask,open('{}p_in_mask_ground_truth_thresh{}.pkl'.format(outdir,thresh),'w'))
    pickle.dump(log_probability_not_in_mask,open('{}p_not_in_ground_truth_thresh{}.pkl'.format(outdir,thresh),'w'))
    pickle.dump(qp,open('{}qp_ground_truth_thresh{}.pkl'.format(outdir,thresh), 'w'))
    pickle.dump(qn,open('{}qn_ground_truth_thresh{}.pkl'.format(outdir,thresh), 'w'))

def do_EM_for(sample_name, objid, num_iterations=5,load_p_in_mask=False,thresh=0,rerun_existing=False,exclude_isovote=False,compute_PR_every_iter=True):
    print "Doing EM"
    outdir = '{}{}/obj{}/'.format(PIXEL_EM_DIR, sample_name, objid)
    if exclude_isovote: 
	mode ='iso'
    else:
	mode =''
    if rerun_existing:
        if os.path.isfile('{}EM_prj_thresh{}.json'.format(outdir,thresh)):
            print "Already ran, Skipped"
            return
    # initialize MV mask
    gt_est_mask = get_MV_mask(sample_name, objid)
    worker_masks = get_all_worker_mega_masks_for_sample(sample_name, objid)
    Nworkers= len(worker_masks)
    mega_mask = get_mega_mask(sample_name, objid)
    for it in range(num_iterations):
        worker_qualities = dict()
        for wid in worker_masks.keys():
            worker_qualities[wid] = worker_prob_correct(mega_mask,worker_masks[wid], gt_est_mask,Nworkers,exclude_isovote=exclude_isovote)
	if load_p_in_mask:
	    #print "loaded pInT" 
	    log_probability_in_mask=pkl.load(open('{}{}p_in_mask_{}.pkl'.format(outdir,mode, it)))
	    log_probability_not_in_mask =pkl.load(open('{}{}p_not_in_mask_{}.pkl'.format(outdir,mode, it)))	
	else: 
	    #Compute pInMask and pNotInMask 
            log_probability_in_mask, log_probability_not_in_mask = mask_log_probabilities(worker_masks, worker_qualities)
	    with open('{}{}p_in_mask_{}.pkl'.format(outdir, mode,it), 'w') as fp:
                fp.write(pickle.dumps(log_probability_in_mask))
            with open('{}{}p_not_in_mask_{}.pkl'.format(outdir,mode, it), 'w') as fp:
                fp.write(pickle.dumps(log_probability_not_in_mask))
        gt_est_mask = estimate_gt_from(log_probability_in_mask, log_probability_not_in_mask,thresh=thresh)
        pickle.dump(log_probability_in_mask,open('{}{}p_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh),'w'))
        pickle.dump(log_probability_not_in_mask,open('{}{}p_not_in_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh),'w'))
        with open('{}{}gt_est_mask_{}_thresh{}.pkl'.format(outdir,mode, it,thresh), 'w') as fp:
            fp.write(pickle.dumps(gt_est_mask))
        pickle.dump(worker_qualities,open('{}{}Qj_{}_thresh{}.pkl'.format(outdir, mode,it,thresh), 'w'))

	# Compute PR mask based on the EM estimate mask from the last iteration
	if compute_PR_every_iter:
            [p, r, j] = get_precision_recall_jaccard(gt_est_mask, get_gt_mask(objid))
            with open('{}{}EM_prj_thresh{}.json'.format(outdir,mode,thresh), 'w') as fp:
                fp.write(json.dumps([p, r, j]))
    plt.figure()
    plt.imshow(gt_est_mask, interpolation="none")  # ,cmap="rainbow")
    plt.colorbar()
    plt.savefig('{}{}EM_mask_thresh{}.png'.format(outdir,mode,thresh))
    if not compute_PR_every_iter:
        # Compute PR mask based on the EM estimate mask from the last iteration
        [p, r, j] = get_precision_recall_jaccard(gt_est_mask, get_gt_mask(objid))
        with open('{}{}EM_prj_thresh{}.json'.format(outdir,mode,thresh), 'w') as fp:
            fp.write(json.dumps([p, r, j]))


def compile_PR(mode=""):
    import glob
    import csv
    with open('{}{}full_PRJ_table.csv'.format(PIXEL_EM_DIR,mode), 'w') as csvfile:
	if mode=="":
            fieldnames = ['num_workers', 'sample_num', 'objid', 'thresh', 'MV_precision', 'MV_recall','MV_jaccard', 'EM_precision', 'EM_recall','EM_jaccard']
	else: # no MV columns 
	    fieldnames = ['num_workers', 'sample_num', 'objid', 'thresh', 'EM_precision', 'EM_recall','EM_jaccard']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for sample_path in glob.glob('{}*_rand*/'.format(PIXEL_EM_DIR)):
            sample_name = sample_path.split('/')[-2]
	    print "Working on ", sample_path
            num_workers = int(sample_name.split('w')[0])
            sample_num = int(sample_name.split('d')[-1])
            for obj_path in glob.glob('{}obj*/'.format(sample_path)):
                objid = int(obj_path.split('/')[-2].split('j')[1])
                mv_p = None
                mv_r = None
		mv_j = None
                em_p = None
                em_r = None
		em_j = None
		if mode =="":
                    mv_pr_file = '{}MV_prj.json'.format(obj_path)
		    if os.path.isfile(mv_pr_file):
                        [mv_p, mv_r,mv_j] = json.load(open(mv_pr_file))
		for thresh_path in glob.glob('{}{}_EM_prj_iter4_thresh*.json'.format(obj_path,mode)):
		    thresh= int(thresh_path.split('/')[-1].split('thresh')[1].split('.')[0])
		    #print thresh
                    em_pr_file = '{}{}_EM_prj_iter4_thresh{}.json'.format(obj_path,mode,thresh)
                    if os.path.isfile(em_pr_file):
                        [em_p, em_r,em_j] = json.load(open(em_pr_file))
                    if any([prj is not None for prj in [mv_p, mv_r, mv_j, em_p, em_r,em_j]]):
			if mode =="": 
			    writer.writerow(
				  {
				    'num_workers': num_workers,
				    'sample_num': sample_num,
				    'objid': objid,
				    'thresh':thresh,
				    'MV_precision': mv_p,
				    'MV_recall': mv_r,
				    'MV_jaccard':mv_j,
				    'EM_precision': em_p,
				    'EM_recall': em_r,
				    'EM_jaccard':em_j
				  }
			     )
			else: 
			    writer.writerow(
                                  {
                                    'num_workers': num_workers,
                                    'sample_num': sample_num,
                                    'objid': objid,
                                    'thresh':thresh,
                                    'EM_precision': em_p,
                                    'EM_recall': em_r,
                                    'EM_jaccard':em_j
                                  }
                             )
    print 'Compiled PR to :'+'{}{}_full_PRJ_table.csv'.format(PIXEL_EM_DIR,mode) 


if __name__ == '__main__':
    #for objid in range(1, 48):
    #    create_all_gt_and_worker_masks(objid)
    #print sample_specs.keys()
    # ['25workers_rand0', '5workers_rand8', '5workers_rand9', '5workers_rand6', '5workers_rand7', '5workers_rand4', '5workers_rand5', '5workers_rand2', '5workers_rand3', '5workers_rand0', '5workers_rand1', '20workers_rand1', '20workers_rand2', '20workers_rand3', '20workers_rand0', '10workers_rand1', '10workers_rand0', '10workers_rand3', '10workers_rand2', '10workers_rand5', '10workers_rand4', '10workers_rand7', '10workers_rand6', '30workers_rand0', '25workers_rand1', '15workers_rand2', '15workers_rand3', '15workers_rand0', '15workers_rand1', '15workers_rand4', '15workers_rand5']
    #sample_lst = sample_specs.keys()
    #sample = sys.argv[1]
    #print sample
    #sample = '5workers_rand0'
    object_lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 42, 43, 44, 45, 46, 47]
    #if True: 
    #for sample in sample_lst[:]:
    # First 7 objects are bad objects, last 3 are good objects
    test_sample_obj = [('10workers_rand5',8),('10workers_rand3',20),('5workers_rand3',20),('5workers_rand3',28),('30workers_rand0',7),\
 			('25workers_rand1',37),('20workers_rand2',11),('25workers_rand0',27),('5workers_rand0',1),('20workers_rand3',32)]
    for test_sample in [('10workers_rand5',8),('5workers_rand0',1)] :# test_sample_obj[-2:]: 
	sample = test_sample[0]
        print '-----------------------------------------------'
        print 'Starting ', sample
        sample_start_time = time.time()
        #for objid in [1]:#object_lst:
	obj = test_sample[1]
 	for objid in [obj]:
	    print "Obj: " ,objid 
            obj_start_time = time.time()
            #create_mega_mask(objid, PLOT=True, sample_name=sample)
            #create_MV_mask(sample, objid)#,mode="compute_pr_only")
            for thresh in [-4,-2,0,2,4]:
	    #for thresh in [0]:
     		print "Working on threshold: ",thresh
    	        #do_EM_for(sample, objid,thresh=thresh,compute_PR_every_iter=False,exclude_isovote=True)#,load_p_in_mask=True,thresh=thresh)
		#do_GTLSA_EM_for(sample, objid,thresh=thresh,rerun_existing=False)
		#do_GT_EM_for(sample, objid,thresh=thresh,exclude_isovote=True,compute_PR_every_iter=True)
		GroundTruth_doM_once(sample, objid,thresh=thresh)
            obj_end_time = time.time()
            print '{}: {}s'.format(objid, round(obj_end_time - obj_start_time, 2))
            sample_end_time = time.time()
            print 'Total time for {}: {}s'.format(sample, round(sample_end_time - sample_start_time, 2))

    #compile_PR(mode="GT")
