#!/usr/bin/env python

#######################################################
#
# cgp_ppCGPMwrapper.py
#
# Programmer:  Carol L. Ecale Zhou
# Last update:  12 April 2020
#
# This script has no required input files, but should be run in the
# directory contining a set of "Results_" directories containing output
# generated by compareGeneProfiles_main.py.
#
# How the script works:
# 1) ppCGPMwrapper.py constructs the necessary command-line arguments for 
# calling postProcessCGPM.py. The output of postProcessCGPM.py is written
# to the current working directory, so ppCGPMwrapper.py changes to the
# specific results directory for a comparison before executing. 
# 2) The directory list (i.e., list of directory names beginning with "Results_")
# is read into a 
# data structure, from which each specific results directory is read, and
# each cycle of postProcessCGPM.py is executed.
# 3) In each directory is located an output file from compareGeneProfiles_main.py, 
# called, compareGeneProfiles_main.log. This log file contains the fully
# qualified directory path/filename for genome1 and genome2. These are read
# by ppCGPMwrapper.py and used to determine which genome file should be #1
# and which #2. 
#
#################################################################
# This code was developed by Carol L. Ecale Zhou at Lawrence Livermore National Laboratory.
# THIS CODE IS COVERED BY THE GPL-3 LICENSE. SEE INCLUDED FILE GPL-3.PDF FOR DETAILS.


import sys, os, re, string, copy
from subprocess import call
import subprocess

# Set messaging booleans
PHATE_PROGRESS = False
PHATE_MESSAGES = False
PHATE_WARNINGS = False
PHATE_PROGRESS_STRING = os.environ["PHATE_PHATE_PROGRESS"]
PHATE_MESSAGES_STRING = os.environ["PHATE_PHATE_MESSAGES"]
PHATE_WARNINGS_STRING = os.environ["PHATE_PHATE_WARNINGS"]
if PHATE_PROGRESS_STRING.lower() == 'true':
    PHATE_PROGRESS = True
if PHATE_MESSAGES_STRING.lower() == 'true':
    PHATE_MESSAGES = True
if PHATE_WARNINGS_STRING.lower() == 'true':
    PHATE_WARNINGS = True

if PHATE_PROGRESS:
    print("cgp_ppCGPMwrapper says, Begin post-process CGPM wrapper code.")

#### CONFIGURABLE

PYTHON_CODE_HOME = "/home/zhou4/PythonCode/BetaCode_CGP/"
POST_PROCESS_CGPM_CODE = PYTHON_CODE_HOME + "postProcessCGPM.py"  # use current stable version or modify constant
CGPM_REPORT = "compareGeneProfiles_main.report"
CGPM_LOG    = "compareGeneProfiles_main.log"

# PATTERNS for recognizing genome 1's & 2's genome and annotation files

p_g1 = re.compile('\#1.*\.fasta')
p_g2 = re.compile('\#2.*\.fasta')
p_a1 = re.compile('\#1.*\.gff')
p_a2 = re.compile('\#2.*\.gff')

#### FILES

logFile = "ppCGPMwrapper.log"
LOGFILE = open(logFile,"w")
LOGFILE.write("%s\n" % ("Begin log file"))
LOGFILE.write("%s%s\n" % ("Version of postProcessCGPM.py being used:",POST_PROCESS_CGPM_CODE))
LOGFILE.write("%s%s\n" % ("PYTHON_CODE_HOME is ",PYTHON_CODE_HOME))

#### CONSTANTS

ACCEPTABLE_ARG_COUNT = (1,2) # "help", "input", or 0 arguments expected

HELP_STRING = "This script does not require input parameters, but should be run in the directory containing the output directories created by compareGeneProfiles_main.py. This script runs postProcessCGPM.py to process the .report files in each Results_ directory and reads the .out file in the current directory to identify the locations of the genome, gene, and protein files that were compared. For more information, type: ppCGPMwrapper.py usage"

USAGE_STRING = "Usage:  ppCGPMwrapper.py\nFor more information, type: ppCGPMwrapper.py help"

INPUT_STRING = "Input:  this program requires no input parameters."

##### Get command-line arguments

argCount = len(sys.argv)
if argCount in ACCEPTABLE_ARG_COUNT:
    if argCount == 2:
        match = re.search("help", sys.argv[1].lower())
        if match:
            print (HELP_STRING)
            exit(0)
        match = re.search("usage", sys.argv[1].lower())
        if match:
            print (USAGE_STRING)
            exit(0)
        match = re.search("input", sys.argv[1].lower())
        if match:
            print (INPUT_STRING)
            exit(0)
else:
    print ("Invalid input parameters. For help, type: ppCGPMwrapper.py help")
    exit(0)

#####

genomeFiles1  = {
    "strain"     : "",  # name of strain (e.g., AmesAncestor)
    "genome"     : "",  # filename containing genome (multi-)fasta
    "annotation" : "",  # filename containing genome annotations
    "genes"      : "",  # filename containing gene sequences 
    "proteins"   : "",  # filename containing protein translations
    }
genomeFiles2  = {
    "strain"     : "",  # name of strain (e.g., AmesAncestor)
    "genome"     : "",  # filename containing genome (multi-)fasta
    "annotation" : "",  # filename containing genome annotations
    "genes"      : "",  # filename containing gene sequences 
    "proteins"   : "",  # filename containing protein translations
    }

# Get list of results directories from previous (compareGeneProfiles_main.py) calculations

command = "ls . | grep \'Results_\'"  # Get list of Results directories in current directory
proc = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True)
(out, err) = proc.communicate()
if err:
    print "ERROR:", err
dirsList = []
dirsList = out.split('\n')

# Walk through each directory name, capture the genome 1 & 2 genome and annotation path/filenames...
# ...then re-construct the gene and protein filenames, and finally, execute postProcessCGPM.py over
# the binary-comparison report file.

if PHATE_PROGRESS:
    print("cgp_ppCGPMwrapper says, Capturing input filenames and computing outfile names.")
count = 0; fragments = []; lineFragments = []
for resultDir in dirsList:
    match = re.search('Results_',resultDir)  # Make sure it's a correct directory name
    if match:  #***                               # Process .report file in this directory
        cgpmReport = CGPM_REPORT  # Construct .report and .log path/filenames
        cgpmLog    = resultDir + '/' + CGPM_LOG 

        ### Get absolute path/filename for genome and annotation files of binary comparison
        CGPM_LOG_HANDLE = open(cgpmLog,"r")  # Log file contains names of genome fasta and annotation files
        fLines = CGPM_LOG_HANDLE.read().splitlines()
        for line in fLines:
            match = re.findall(p_g1,line)  # Genome 1 fasta path/filename in this line
            if match:
                lineFragments = line.split(' ')
                genomeFiles1["genome"] = lineFragments[3] # in 4th position, if you split on space
                fragments = genomeFiles1["genome"].split('.fasta')
                genomeFiles1["genes"]    = fragments[0] + '_gene.fasta' # reconstruct genes fasta filename
                genomeFiles1["proteins"] = fragments[0] + '_prot.fasta'
                continue 
            match = re.findall(p_g2,line)  # Genome 2 fasta path/filename in this line
            if match:
                lineFragments = line.split(' ')
                genomeFiles2["genome"] = lineFragments[3]
                fragments = genomeFiles2["genome"].split('.fasta')
                genomeFiles2["genes"]    = fragments[0] + '_gene.fasta'
                genomeFiles2["proteins"] = fragments[0] + '_prot.fasta'
                continue 
            match = re.findall(p_a1,line)  # Genome 1 annotation path/filename in this line
            if match:
                lineFragments = line.split(' ')
                genomeFiles1["annotation"] = lineFragments[3]
                continue 
            match = re.findall(p_a2,line)  # Genome 2 annotation path/filename in this line
            if match:
                lineFragments = line.split(' ')
                genomeFiles2["annotation"] = lineFragments[3]
                continue 
        CGPM_LOG_HANDLE.close() 
        
        # Run postProcessCGMP.py for the current binary comparison
        currentDir = os.getcwd()  # where are we now
        os.chdir(resultDir)       # change to current Results directory
        call(["python",POST_PROCESS_CGPM_CODE,"-g1",genomeFiles1["genes"],"-g2",genomeFiles2["genes"],"-r",cgpmReport])
        os.chdir(currentDir)      # return
        count += 1 
        LOGFILE.write("%s%s\n" % ("Completed post-processing in directory ",resultDir))
        if PHATE_PROGRESS:
            print("cgp_ppCGPMwrapper says, Completed post-processing in directory ",resultDir)

##### Clean up

LOGFILE.write("%s%s%s\n" % ("Execution complete. ",count," jobs completed." ))
if PHATE_PROGRESS:
    print ("cgp_ppCGPMwrapper says, Execution complete.", count, "jobs completed.")
LOGFILE.close()
