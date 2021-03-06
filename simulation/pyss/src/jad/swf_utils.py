'''
	Utilities function used to manipulate swf log files.
'''


from itertools import compress, dropwhile, izip

from io_utils import *

swf_skip_hdr = lambda u: u.lstrip().startswith(';');
swf_skip_hdr_itr = lambda _file: dropwhile(swf_skip_hdr, _file)


def split_swf(in_file_name, tpercent, parts, dir="./"):

	jobs = []
	with open(in_file_name) as f:
		for line in dropwhile(swf_skip_hdr, f):
			jobs.append(line.strip());

	# from random import shuffle
	# shuffle(jobs)
	file_name = simple_name(in_file_name)

	training_size = int(len(jobs) * tpercent)
	part_size = training_size / parts
	training_size = part_size * parts

	str_name_format = "%s/%s_part%%d.swf" % (dir, file_name)

	training_files = []

	for i in range(parts):
		fname = str_name_format % (i+1)
		training_files.append(fname)
		write_lines_to_file(fname, jobs[i*part_size:(i+1)*part_size])

	test_file = "%s/%s_test.swf" % (dir, file_name)
	write_lines_to_file(test_file, jobs[training_size:])

	print "#parts={0} part_size={1} test_set_size={2}".format(parts, part_size, len(jobs)-training_size)
	return training_files, test_file


def extract_columns(fname, indices=None):

	if indices is not None:
		mask = [i in indices for i in range(1, 19)]
		size = mask.count(True)
	else:
		size = 18
		mask = [True] * 18

	cols = [[] for i in range(size)]
	with open(fname) as f:
		for line in dropwhile(swf_skip_hdr, f):
			job = [u for u in line.strip().split()];
			row = compress(job, mask)
			row = [float(u) for u in row];
			for col, val in izip(cols, row):
				col.append(val)

	return cols

def extract_columns_from_itr(itr, indices=None):

	if indices is not None:
		mask = [i in indices for i in range(1, 19)]
		size = mask.count(True)
	else:
		size = 18
		mask = [True] * 18

	cols = [[] for i in range(size)]
	for line in itr:
		job = [u for u in line.strip().split()];
		row = compress(job, mask)
		row = [float(u) for u in row];
		for col, val in izip(cols, row):
			col.append(val)

	return cols

def normalize(lst, min_max=None):
	if min_max is None:
		mn, mx = min(lst), max(lst)
	else:
		mn, mx = min_max[0], min_max[1]
	rng = mx - mn;
	if rng == 0: return [0] * len(lst)
	return map(lambda u: (u-mn)/rng, lst)

def normalize_mat(mat, min_max):
	#print "normalize_mat", len(mat), len(min_max), min_max, mat
	return map(lambda u: normalize(u[0], u[1]), izip(mat, min_max))

def convert_to_ml_format_(lst, qid):

	cat_num = 10
	ct_size = len(lst[0]) / cat_num + 1
	rng = range(1, len(lst)+1)
	score = cat_num+1;
	lines = []
	for i in xrange(len(lst[0])):
		l = [p[i] for p in lst]
		t = ' '.join(map(lambda v: "%d:%f" % v, zip(rng, l)))
		lines.append("{0} qid:{1} {2}".format(score, qid, t))
		if (i+1)%ct_size==0: score-=1

	return lines

def convert_to_ml_format(lst, qid):

	fmt = ' '.join(map(lambda v: "%d:%%f" % (v+1), range(len(lst))))
	score = 1000000-1;
	lines = []
	for i in xrange(len(lst[0])):
		t = fmt % tuple([p[i] for p in lst])
		lines.append("{0} qid:{1} {2}".format(score, qid, t))
		score-=1

	return lines

	rng = range(1, len(lst)+1)
	score = 1000000-1;
	lines = []
	for i in xrange(len(lst[0])):
		l = [p[i] for p in lst]
		t = ' '.join(map(lambda v: "%d:%f" % v, zip(rng, l)))
		lines.append("{0} qid:{1} {2}".format(score, qid, t))
		score-=1

	return lines

def convert_job_to_ml_format(job, score=0, qid=0):
	fmt = ' '.join(map(lambda v: "%d:%%s" % (v+1), range(len(job))))
	return "{0} qid:{1} {2}".format(score, qid, fmt % job)

def convert_jobs_to_ml_format(jobs, qid):

	fmt = ' '.join(map(lambda v: "%d:%%s" % (v+1), range(len(jobs[0]))))
	score = 1000000-1;
	lines = []
	for job in jobs:
		lines.append("{0} qid:{1} {2}".format(score, qid, fmt % job))
		score-=1

	# return lines
	return '\n'.join(lines)

def convert_to_ml_format_from_file(fname, qid, indices=None):

	if indices is not None:
		mask = [i in indices for i in range(1, 19)]
		size = mask.count(True)
	else:
		size = 18
		mask = [True] * 18

	rng = range(1, size+1)

	score = 1000000-1;
	lines = []
	with open(fname) as f:
		for line in dropwhile(swf_skip_hdr, f):
			job = [int(float(u)) for u in line.strip().split()];
			l = compress(job, mask)
			t = ' '.join(map(lambda v: "%d:%d" % v, zip(rng, l)))
			lines.append("{0} qid:{1} {2}".format(score, qid, t))
			score-=1

	return lines



def getMaxProcs(fname):
	with open(fname) as f:
		for line in f.readlines():
			if "; MaxProcs:" in line:
				return int(line.strip().split()[-1])
	raise NameError('No MaxProcs in the log\'s header')


def compute_utilisation(fname):
	first, last, procs, sum_area = float("inf"), 0, getMaxProcs(fname), 0
	with open(fname) as f:
		for line in dropwhile(swf_skip_hdr, f):
			st, wt, rt, pr = [float(v) for v in [u for u in line.strip().split()][1:5]]
			first = min(first, st + wt)
			last = max(last, wt + rt + st)
			sum_area += rt * pr

	ratio = sum_area / (1.0 * procs * (last-first))
	return ratio

# def split_by_time(in_file_name, dir="./"):

def statistics(fname):
	RT, PR = [], []
	with open(fname) as f:
		for line in dropwhile(swf_skip_hdr, f):
			st, wt, rt, pr = [float(v) for v in [u for u in line.strip().split()][1:5]]
			RT.append(rt)
			PR.append(pr)
	print "min run-time", min(RT)
	print "min processors", min(PR)
	print "min run-time", sorted(RT)[10000:10200]
	print "min processors", sorted(PR)[10000:10200]

# statistics("logs/CEA-curie_log.swf")
# statistics("logs/KTH-SP2_log.swf")


def classify_jobs(fname):
	runtime_limit = 60*60 # second
	processors_limit = 8
	SN, LN, LW, SW = 0, 0, 0, 0
	total_jobs = 0.0
	with open(fname) as f:
		for line in dropwhile(swf_skip_hdr, f):
			total_jobs += 1
			rt, pr = [float(v) for v in [u for u in line.strip().split()][3:5]]
			if rt <= runtime_limit:
				if pr <= processors_limit:
					SN+=1
				else:
					SW+=1
			else:
				if pr <= processors_limit:
					LN+=1
				else:
					LW+=1

	print fname
	print "     |   N   |   W"
	print "  S  | %.2f  | %.2f" % (100*SN/total_jobs, 100*SW/total_jobs)
	print "  L  | %.2f  | %.2f" % (100*LN/total_jobs, 100*LW/total_jobs)
	print
	return total_jobs
