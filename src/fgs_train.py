#!/usr/bin/env python

'''fgs_train.py: produce needed training data set for running FragGeneScan HMM model
file can be trained: gene, rgene, noncoding, start, end, start1, end1

Usage:

fgs_train.py -i input_gene_seq.csv [-n input_noncoding_seq.csv] [-g]

with -g, it will stratify genes by gc content (from 26% to 70%)
without -g, it will not stratify, but for compatibility with FragGeneScan, 
the output file also contains 45 groups of probability data, only difference 
is that every group has the same data.
''' 


import os
from optparse import OptionParser

nt_list = ['A', 'C', 'G', 'T']

nt_dict = {'A':0, 'C': 1, 'G':2, 'T':3, 
           'a':0, 'c':1, 'g':2, 't':3}

complement_dict = {'A':'T', 'C': 'G', 'G':'C', 'T':'A', 
           'a':'t', 'c':'g', 'g':'c', 't':'a'}

STRATIFY = False

MIN_GC_CONTENT = 26
MAX_GC_CONTENT = 70
NUM_STRATIFY = 45
NUM_M_STATE = 6
NUM_DIMER = 16
NUM_NT = 4

def trimer_to_int(triplet):
    '''return number by triplet'''
    t1 = nt_dict.get(triplet[0])
    t2 = nt_dict.get(triplet[1])
    t3 = nt_dict.get(triplet[2])
    
    if t1 >= 0 and t2 >=0 and t3 >=0:
        return t1 * 16 + t2 * 4 + t3
    else:
        return -1
    
def get_gc_content(sequence):
    '''return gc_content% of a given sequence'''
    gc_count = 0
    for ch in sequence:
        if ch in ['G', 'C', 'g', 'c']:
            gc_count += 1
#    print "%f\t%f\t%f"%(float(gc_count) / len(sequence), round(float(gc_count) / len(sequence), 2) * 100, int(round(float(gc_count) / len(sequence), 2) * 100)  ) 
    gc_content = int(float(gc_count) / len(sequence) * 100 + 0.5)
    #print "gc countent %s rounded to %s" % (float(gc_count) / len(sequence) * 100, gc_content)
    if gc_content < MIN_GC_CONTENT:
        gc_content = MIN_GC_CONTENT
    if gc_content > MAX_GC_CONTENT:
        gc_content = MAX_GC_CONTENT
    return gc_content

def parse_input_file(filename):
    '''parse the input file'''
    infile = open(filename, "r")
    seq_lists = []
    linenumber = 0    
    for line in infile:
        line = line.strip('\n')
        line = line.strip('\r')
        splits = line.split('\t')
        linenumber += 1
        if len(splits) == 3:
            seq_len = len(splits[2])
            if seq_len > 0:
                if seq_len < 123:
                    print "**********************************************"
                    print "Warning!!:the input data contains invalid data, line %d, sequence length=%s" % (linenumber, seq_len)
                    print "The invalid sequence is thrown out to continue, but replacing input data and re-training is suggested." 
                    print "**********************************************"
                    continue
                seq_lists.append(splits[2])
    return seq_lists
    
def train_gene_transition(seq_list, output_file):
    '''train transition probability of matching states'''
    
    e_M_counts = [[[[0 for i in range(4)] for j in range(16)] for m in range(6)] for g in range(NUM_STRATIFY) ]
        
    for seq in seq_list:
        
        if STRATIFY:
            gc_content = get_gc_content(seq)
            
        else:
            gc_content = MIN_GC_CONTENT        
        
#        print "gc_content=", gc_content
        
        for i in range(60, len(seq)-63):  #iterate coding NTs
            m = i % 6  #m = 0..5 representing M state from11..6
            to = nt_dict.get(seq[i], -1)
            from0 = nt_dict.get(seq[i-2], -1)
            from1 = nt_dict.get(seq[i-1], -1)
            if from0 >= 0 and from1 >= 0:
                from2 = from0 * 4 + from1
                e_M_counts[gc_content-MIN_GC_CONTENT][m][from2][to] += 1
            
    gene_file = open(output_file, "w")
    
    for gc in range(MIN_GC_CONTENT, MAX_GC_CONTENT + 1):
        line = "%s\n" % gc
        gene_file.write(line)
        
        if STRATIFY:
            k = gc
        else:
            k = MIN_GC_CONTENT  
        
        for m in range(6):
        #print "position=", m+1
            for j in range(16):
                total_ct = sum(e_M_counts[k - MIN_GC_CONTENT][m][j]) + 1
                #  print dimer_list[j],
                line = "";
                for i in range(4):
                    if total_ct > 0:
                        ct = e_M_counts[k-MIN_GC_CONTENT][m][j][i]
                        if ct == 0:
                            prob = 0.0001
                        else:
                            prob = round(float(ct) / total_ct, 4)
                    else:
                        prob = 0.0001
                    line += str(prob)
                    line += '\t'
                line = line.strip('\t')
                line += ('\n')
                gene_file.write(line)
    
    gene_file.close()
    print "output file produced: %s" % output_file 
     
def train_gene_transition_two_way(seq_list):
    '''train gene transition probability files for two ways'''
    train_gene_transition(seq_list, "gene")
    rc_req_list = []
    for seq in seq_list:
        rc_req_list.append(get_reverse_complement(seq))
    train_gene_transition(rc_req_list, "rgene") 
    
def get_start_stop_subseq(seq, key):
    '''return the subsequence to check for training start/end/start1/end1'''
    
    rc_seq = get_reverse_complement(seq)
    
    if key=="start":
        subseq = seq[30:93]
    elif key=="end":
        subseq = seq[-123:-60]
    elif key=="start1":
        subseq = rc_seq[-93:-30]
    elif key=="end1":
        subseq = rc_seq[60:123]
    else:
        subseq = seq
    return subseq       
    
    
def train_start_stop_adjacent_prob(seq_list):
    '''train start, end, start1, end1, stratify by gene GC content'''
    
    prob_counts_dict = {"start": [[[0 for i in range(64)] for j in range(61)] for g in range(NUM_STRATIFY)],
                        "end" : [[[0 for i in range(64)] for j in range(61)] for g in range(NUM_STRATIFY)],
                        "start1": [[[0 for i in range(64)] for j in range(61)] for g in range(NUM_STRATIFY)],
                        "end1": [[[0 for i in range(64)] for j in range(61)] for g in range(NUM_STRATIFY)]}
                        
    for seq in seq_list:
        
        if STRATIFY:
            gc_content = get_gc_content(seq)
        else:
            gc_content = MIN_GC_CONTENT        
            #os.stderr.write("%d\n"%gc_content); 
        for key in prob_counts_dict.keys():
            subseq = get_start_stop_subseq(seq, key)
            for i in range(61):
                s_triplet = subseq[i:i+3]
                index = trimer_to_int(s_triplet)
                prob_counts_dict[key][gc_content-MIN_GC_CONTENT][i][index] += 1
    
    for key in prob_counts_dict.keys():
        write_start_stop_file(key, prob_counts_dict[key])
              
def write_start_stop_file(filename, prob_counts):
    '''write start stop prob into output files, with gc'''
    outfile = open(filename, "w")
    for gc in range(MIN_GC_CONTENT, MAX_GC_CONTENT + 1):
        line = "%s\n" % gc
        outfile.write(line)
        
        if STRATIFY:
            k = gc
        else:
            k = MIN_GC_CONTENT
        
        for i in range(61):
            line = "";
            total_ct = sum(prob_counts[k - MIN_GC_CONTENT][i])
            for j in range(64):
                if total_ct > 0:
                    prob = round(float(prob_counts[k - MIN_GC_CONTENT][i][j] + 1) / (total_ct + 1), 6)
                else:
                    prob = 0.000001
                line += str(prob)
                line += '\t'
            line = line.strip('\t')
            line += ('\n')
            outfile.write(line)
    outfile.close()
    print "output file produced: %s" % filename
            
def get_reverse_complement(seq):
    '''return the reverse complement of the given sequence'''
    seq = seq[::-1]
    rseq= ""
    for ch in seq:
        try:
            rseq += complement_dict[ch]
        except KeyError:
            rseq += "N"
    return rseq            

def train_non_coding(seq_list):
    '''train noncoding file'''
    
    r_r_counts = [[[0 for i in range(4)] for j in range(4)] for g in range(NUM_STRATIFY)]
        
    for seq in seq_list:
        if STRATIFY:
            gc_content = get_gc_content(seq)
        else:
            gc_content = MIN_GC_CONTENT        
        
        for t in range(len(seq)-1):
            fr = nt_dict.get(seq[t], -1)
            to = nt_dict.get(seq[t+1], -1)
                  
            if fr >= 0 and to >= 0:
                r_r_counts[gc_content - MIN_GC_CONTENT][fr][to] += 1
            
    noncoding_file = open("noncoding", "w")
    
    for gc in range(MIN_GC_CONTENT, MAX_GC_CONTENT+1):
        line = "%s\n" % gc
        noncoding_file.write(line)
        
        if STRATIFY:
            k = gc
        else:
            k = MIN_GC_CONTENT  
        
        for j in range(4):
            total_ct = sum(r_r_counts[k - MIN_GC_CONTENT][j])
            for i in range(4):
                #  print dimer_list[j],
                line = "";
                for i in range(4):
                    if total_ct > 0:
                        ct = r_r_counts[k-MIN_GC_CONTENT][j][i]
                        if ct == 0:
                            prob = 0.0001
                        else:
                            prob = round(float(ct) / total_ct, 4)
                    else:
                        prob = 0.0001
                    line += str(prob)
                    line += '\t'
                line = line.strip('\t')
                line += ('\n')
                noncoding_file.write(line)                    
                                  
    noncoding_file.close()
    print "output file produced: noncoding"                                
            
if __name__ == '__main__':
    usage  = "usage: %prog -i <input sequence file> -n <input noncoding file> [-g]"
    parser = OptionParser(usage)
    parser.add_option("-i", "--input",  dest="input", type = "string", default=None, help="Input gene sequence file.")
    parser.add_option("-n", "--noncoding",  dest="noncoding", type = "string", default=None, help="Input noncoding sequence file.")
    parser.add_option("-g", "--gc", dest="gc_content", action="store_true", default=False, help="stratify by gene GC content")
    
    (opts, args) = parser.parse_args()
    
    STRATIFY = opts.gc_content
    
    msg = "Stratify= %s" % STRATIFY
    if STRATIFY==False:
        msg += ", use -g to enable gc_content stratification"
    print msg    
 
    if not (opts.input and os.path.isfile(opts.input) ):
        parser.error("Missing input file %s"%(opts.input, ))
        
    inputFile = opts.input 
    
    seq_list = parse_input_file(inputFile)
    print "total # of sequences=", len(seq_list)
    

    
    train_gene_transition_two_way(seq_list)
    train_start_stop_adjacent_prob(seq_list)
    
    if opts.noncoding and os.path.isfile(opts.noncoding):
        noncoding_seq_list = parse_input_file(opts.noncoding)
        train_non_coding(noncoding_seq_list)
        
        
    
