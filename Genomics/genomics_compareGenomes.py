#################################################################################
# Module: genomics_compareGenomes.py
#
# Programmer:  Carol L. Ecale Zhou
#
# Most recent update: 19 May 2020
#
# Module comprising classes and data structures for comparing genomes
#
# Classes and Methods:
#    class comparison
#       performComparison()
#       ---data input
#       loadData()
#       readDirectories()
#       parseDirectories()
#       parseReportFiles()
#       findGenomes()
#       loadBestHits()
#       getGeneCallString()
#       addHit2genome()
#       findGenomeObject()
#       ---comparison
#       identifyParalogs()
#       computeHomologyGroups()
#       saveHomologyGroups()
#       ---verification
#       countGenomes()
#       checkUnique()
#       ---reporting
#       writeCoreGenome()
#       writeCorrespondences()
#       writeMutualBestHitList()
#       writeSingularBestHitList()
#       writeLonerList()
#       printReport()
#       printAll()
#    class genome
#       ---comparison
#       identifyParalogs()
#       ---verification
#       checkUnique()
#       ---reporting
#       printReport()
#       printAll()
#    class paralogSet
#       ---verification
#       countParalogs()
#       ---reporting
#       printReport()
#       printAll()
#    class gene_protein
#       ---data input
#       addMutualBestHit()
#       addSingularBestHit()
#       addGroupMember()
#       ---verification
#       verifyLoner()
#       ---reporting
#       writeMutualBestHitList()
#       writeSingularBestHitList()
#       writeLonerList()
#       printReport()
#       printAll()
#
#################################################################################

# This code was developed by Carol. L. Ecale Zhou at Lawrence Livermore National Laboratory.
# THIS CODE IS COVERED BY THE BSD LICENSE. SEE INCLUDED FILE BSD.PDF FOR DETAILS.

import re, os, copy
import subprocess
import ast

CODE_BASE_DIR    = ""
OUTPUT_DIR       = ""

# Verbosity

PHATE_WARNINGS = False
PHATE_MESSAGES = False
PHATE_PROGRESS = False

PHATE_WARNINGS_STRING = os.environ["PHATE_PHATE_WARNINGS"]
PHATE_MESSAGES_STRING = os.environ["PHATE_PHATE_MESSAGES"]
PHATE_PROGRESS_STRING = os.environ["PHATE_PHATE_PROGRESS"]

if PHATE_WARNINGS_STRING.lower() == 'true':
    PHATE_WARNINGS = True

if PHATE_MESSAGES_STRING.lower() == 'true':
    PHATE_MESSAGES = True

if PHATE_PROGRESS_STRING.lower() == 'true':
    PHATE_PROGRESS = True

# Override
PHATE_PROGRESS = True
PHATE_WARNINGS = True
PHATE_MESSAGES = True

DEBUG = False
DEBUG = True

# Locations and files
CGP_RESULTS_DIR      = os.environ["PHATE_CGP_RESULTS_DIR"]
GENOMICS_RESULTS_DIR = os.environ["PHATE_GENOMICS_RESULTS_DIR"]
CGP_LOG_FILE         = "compareGeneProfiles_main.log"           # Lists genome fasta and annotation files
CGP_REPORT_FILE      = "compareGeneProfiles_main.report"        # Tabbed file with gene-gene listing
CGP_PARALOG_FILE     = "compareGeneProfiles_main.paralogs"      # Paralogs detected by CGP; text format 
CGP_OUT_FILE         = "compareGeneProfiles_main.out"           # Same data as report file, but in python list format
CGP_SUMMARY_FILE     = "compareGeneProfiles_main.summary"       # High-level summary of genome-genome comparison

# Report file fields
SORT_POSITION        = 0
GENOME_TYPE          = 1
QUERY_START          = 2
QUERY_END            = 3
SUBJECT_START        = 4
SUBJECT_END          = 5
IDENTITY             = 6
E_VALUE              = 7
G1_Q_S_LONER         = 8
G1_HEADER            = 9
G1_CONTIG            = 10
G1_ANNOTATIONS       = 11
G1_GENE_START        = 12
G1_GENE_END          = 13
G1_STRAND            = 14
G2_Q_S_LONER         = 15
G2_HEADER            = 16
G2_CONTIG            = 17
G2_ANNOTATIONS       = 18
G2_GENE_START        = 19
G2_GENE_END          = 20
G2_STRAND            = 21
G1_COVERAGE          = 22
G2_COVERAGE          = 23
ALIGNMENT_LENGTH     = 24
GAP_OPENS            = 25
G1_SPAN              = 26
G1_LENGTH            = 27
G2_SPAN              = 28
G2_LENGTH            = 29

# Class comparison organizes all genomic data and performs comparisons, ultimately yielding
#   homology groups for each gene/protein in a reference genome.
class comparison(object):
    
    def __init__(self):

        self.name                  = "multiPhATE2"  # Can assign a set to this genome comparison
        self.directories           = []             # List of Results directories to be processed
        self.referenceGenome       = ""             # name of genome assigned as the reference
        self.genomeCount           = 0              # number of genomes in set
        self.genomeList            = []             # set of genome class objects
        self.commonCore            = []             # list of genes that are common among all genomes; how to define exactly???
        self.geneHomologyGroups    = []             # closely related genes for hmmbuild (list of lists)
        self.proteinHomologyGroups = []             # closely related proteins for hmmbuild (list of lists)
        # Templates
        self.genomeTemplate        = genome()
        self.geneTemplate          = gene_protein()
        self.geneTemplate.type     = "gene"
        self.proteinTemplate       = gene_protein()
        self.proteinTemplate.type  = "protein"

    def performComparison(self):

        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Loading data.")
        self.loadData()

        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Computing homology groups.")
        self.computeHomologyGroups()
        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Writing homology groups to files.")
        self.saveHomologyGroups()

        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Writing final reports.")
        self.printReport()

    #===== COMPARISON DATA LOAD METHODS

    def loadData(self):
        dirList = self.readDirectories()
        self.parseDirectories(dirList)
        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Data loading complete.")
        return

    def readDirectories(self):
        dirList = []
        # Query Results files in CGP Results directory
        command = "ls " + CGP_RESULTS_DIR
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        (rawresult, err) = proc.communicate()
        result = rawresult.decode('utf-8')
        fileList = str(result).split('\n')   # Python3

        for filename in fileList:
            match_resultdir = re.search('Results_',filename)
            if match_resultdir:
                dirList.append(filename)

        if PHATE_MESSAGES:
            print("genomics_compareGenomes says, The following directories have been read:")
            for directory in dirList:
                print("directory:",directory)
        return dirList

    def parseDirectories(self,dirList):
        # Walk through the CGP output directory; determine which genomes were processed; add them to a non-redundant list
        genomeList = []; genomeFastaList = []
        for directory in dirList:
            cgp_directory = os.path.join(CGP_RESULTS_DIR,directory)
            if PHATE_PROGRESS:
                print("genomics_compareGenomes says, Preparing to load data from directory,",cgp_directory)

            # Read log file; determine two genomes
            CGP_LOG = os.path.join(cgp_directory,CGP_LOG_FILE)
            cgpLog = open(CGP_LOG,'r')
            cLines = cgpLog.read().splitlines()
            for cLine in cLines:
                match_fileLine = re.search('genome\sfile',cLine)
                if match_fileLine:
                    (preamble,filePath) = cLine.split(': ')
                    genomeFasta = os.path.basename(filePath)
                    if genomeFasta not in genomeFastaList:
                        genomeFastaList.append(genomeFasta)
                    (genome,extension) = genomeFasta.split('.')
                    if genome not in genomeList:
                        genomeList.append(genome)
            cgpLog.close()

            # First genome listed is the reference (was listed first in user's config file)
            if genomeList:
                self.referenceGenome = genomeList[0]
            else:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes says, WARNING: There are no genomes to compare.")

        # Create genome objects, one for each genome found in the CGP output directory
        for i in range(0,len(genomeList)):
            nextGenome = copy.deepcopy(self.genomeTemplate)
            nextGenome.name = genomeList[i]
            if nextGenome.name == self.referenceGenome:
                nextGenome.isReference = True
            nextGenome.file = genomeFastaList[i]
            self.genomeList.append(nextGenome)
        #self.countGenomes()

        # Walk through .report files, add mutual & singular best hits, loners
        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Invoking self.parseReportFiles with dirList,",dirList)
        self.parseReportFiles(dirList)
        return

    # Method parseReportFiles pulls data from CGP Results_* directories into memory in order to determine
    # a core genome, gene-gene correspondences among all genomes, and list loner genes per genome.
    def parseReportFiles(self,dirList):
        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Parsing Report files.")
        # Load data for mutual and singular best hits and loners for all CGP binary genome comparisons.
        for i in range(0,len(dirList)):
            directory = dirList[i]
            (genome1,genome2) = self.findGenomes(directory)
            reportFile  = os.path.join(CGP_RESULTS_DIR,directory,CGP_REPORT_FILE)
            paralogFile = os.path.join(CGP_RESULTS_DIR,directory,CGP_PARALOG_FILE)
            if PHATE_PROGRESS:
                print("genomics_compareGenomes says, Parsing report file",reportFile,"for mutual and singular best hits, and loners.")
            self.loadBestHits(genome1,genome2,reportFile)
            self.loadParalogs(paralogFile)

        return

    def findGenomes(self,directory):
        # Determine which 2 genomes's data are listed in this directory,
        # and which is genome1, genome2.
        genome1 = ""; genome2 = ""
        logFile = os.path.join(CGP_RESULTS_DIR,directory,CGP_LOG_FILE)
        LOG_H = open(logFile,"r")
        lLines = LOG_H.read().splitlines()
        for lLine in lLines:
            match_genome1 = re.search('genome\sfile\s#1:',lLine)
            match_genome2 = re.search('genome\sfile\s#2:',lLine)
            if match_genome1:
                (preamble,genomePath) = lLine.split(': ')
                genome1fasta = os.path.basename(genomePath)
                (genome1,extension) = genome1fasta.split('.') 
            if match_genome2:
                (preamble,genomePath) = lLine.split(': ')
                genome2fasta = os.path.basename(genomePath)
                (genome2,extension) = genome2fasta.split('.') 
        LOG_H.close()
        return(genome1,genome2)

    def loadBestHits(self,genome1,genome2,reportFile):
        PROTEIN = False; hitCount = 0
        REPORT_H = open(reportFile,"r")
        rLines = REPORT_H.read().splitlines()

        # Select and process mutual-best-hit data lines
        # Gene hits are loaded first, then protein
        for rLine in rLines:
            fields = []; genomeNum = ""; hitType = ""
            # Skip lines not to be processed in this method
            match_comment = re.search('^#',rLine)
            match_protein = re.search('^#PROTEIN\sHITS',rLine)
            if match_protein: 
                PROTEIN = True  # Prepare for loading protein hits next
            if match_comment:
                continue
            fields = rLine.split('\t')
            (genomeNum,hitType) = fields[GENOME_TYPE].split('_')
            # Data structure for passing parameters to self.addHit2genome()
            dataArgs = { 
                "genome1"      : genome1,   # the fasta file name
                "genome2"      : genome2,   # the fasta file name
                "contig1"      : "",
                "contig2"      : "",
                "gene1"        : "",
                "gene2"        : "",
                "protein1"     : "",
                "protein2"     : "",
                "geneCall1"    : "",
                "geneCall2"    : "",
                "annotations1" : "",
                "annotations2" : "",
                "hitType"      : "",
                "hitFlavor"    : "",
                }

            # Prepare arguments for passing to addHit2genome method
            if genomeNum == "genome1":
                dataArgs["hitType"] = hitType + '1'
            elif genomeNum == "genome2":
                dataArgs["hitType"] = hitType + '2'
            else:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes says, WARNING: Unrecognized GENOME_TYPE")

            # Record data from reportFile dataline
            # Fields pertaining to gene or protein
            dataArgs["contig1"]          = fields[G1_CONTIG]
            dataArgs["contig2"]          = fields[G2_CONTIG]
            dataArgs["annotations1"]     = fields[G1_ANNOTATIONS]
            if dataArgs["annotations1"] != "":
                dataArgs["geneCall1"]    = self.getGeneCallString(fields[G1_ANNOTATIONS]) 
            dataArgs["annotations2"]     = fields[G2_ANNOTATIONS]
            if dataArgs["annotations2"] != "":
                dataArgs["geneCall2"]    = self.getGeneCallString(fields[G2_ANNOTATIONS]) 

            # Protein-, gene-specific fields
            if PROTEIN:
                dataArgs["hitFlavor"]    = "protein"
                dataArgs["protein1"]     = fields[G1_HEADER]
                dataArgs["protein2"]     = fields[G2_HEADER]
            else:
                dataArgs["hitFlavor"]    = "gene"
                dataArgs["gene1"]        = fields[G1_HEADER]
                dataArgs["gene2"]        = fields[G2_HEADER]

            # Insert data record into genome object
            self.addHit2genome(dataArgs)

        REPORT_H.close()
        return

    def loadParalogs(self,paralogFile):
        PARALOG_H = open(paralogFile,"r")
        pLines = PARALOG_H.read().splitlines()

        # Select and process mutual-best-hit data lines
        fields = []; genomeNum = ""; paralogType = ""; genomeName = ""
        GENE = False; PROTEIN = False

        # First, reset dataArgs data structure, for passing parameters to self.addHit2genome
        dataArgs = { 
            "genome1"      : "",   # the fasta file name
            "genome2"      : "",   
            "contig1"      : "",   
            "contig2"      : "",   
            "gene1"        : "",
            "gene2"        : "",
            "protein1"     : "",
            "protein2"     : "",
            "geneCall1"    : "",
            "geneCall2"    : "",
            "annotations1" : "",
            "annotations2" : "",
            "hitType"      : "",
            }

        # Parse data from paralogs report file
        for pLine in pLines:

            # Skip lines not to be processed in this method
            match_comment = re.search('^#',pLine)
            match_blank   = re.search('^$',pLine)
            if match_comment or match_blank:
                continue
            match_genome   = re.search('PARALOGS',         pLine)
            match_gene     = re.search('Gene\sParalogs',   pLine)
            match_protein  = re.search('Protein\sParalogs',pLine)
            match_header   = re.search('header:',          pLine)
            match_hitLine  = re.search('query:',           pLine)
            match_coverage = re.search('coverage:',        pLine)

            # Determine which genome's paralogs are being reported
            if match_genome:
                match_genomePath = re.search('[\w\d\/\.]',pLine)
                if match_genomePath:
                    genomePathString       = match_genomePath.group(0)
                    genomeFileString       = os.path.basename(genomePath)
                    (genomeName,extension) = genomeFileString.split('.')
                    dataArgs["genome1"] = genomeName
                else:
                    if PHATE_WARNINGS:
                        print("genomics_compareGenomes says, WARNING: Cannot read genome path from paralogs file,",paralogFile)
            else:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes says, WARNING: Cannot read genome name from paralogs file,",paralogFile)

            # Determine whether it's a gene versus protein paralog
            if match_gene:
                GENE = True
            if match_protein:
                PROTEIN = True

            # Parse paralog data; add to paralog list 
            if match_hitLine:
                fields = pLine.split('\t')
                queryString        = fields[0]
                subjectString      = fields[1]
                hitType            = fields[2]
                identity           = fields[3]
                alignLength        = fields[4]
                mismatches         = fields[5]
                gapopens           = fields[6]
                queryStartEnd      = fields[7]
                subjectStartEnd    = fields[8]
                (preamble,query)   = queryString.split(':')
                (preamble,subject) = subjectString.split(':')
            if GENE:
                dataArgs["gene1"]    = query
                dataArgs["gene2"]    = subject
                dataArgs["hitType"]  = "gene_paralog"
            elif PROTEIN:
                dataArgs["protein1"] = query
                dataArgs["protein2"] = subject
                dataArgs["hitType"]  = "protein_paralog"

            # Read coverage (last data line per paralog) and add this paralog to genome's paralogList; Then, reset
            if match_coverage:
                coverage = re.search('[\d\.]',pLine)

                # Insert data record into genome object
                self.addParalog2genome(dataArgs)

                # Reset data structures
                dataArgs = { 
                    "genome1"      : "",   # the fasta file name
                    "genome2"      : "",   # not used for paralog hit 
                    "contig1"      : "",   
                    "contig2"      : "",   
                    "gene1"        : "",
                    "gene2"        : "",
                    "protein1"     : "",
                    "protein2"     : "",
                    "geneCall1"    : "",
                    "geneCall2"    : "",
                    "annotations1" : "",
                    "annotations2" : "",
                    "hitType"      : "paralog",
                    }
                GENE       = False
                PROTEIN    = False
                genomeName = ""
                query      = ""
                subject    = ""
                coverage   = 0.0

        PARALOG_H.close()
        return

    def addParalog2genome(self,dataArgs):
        if "genome1" in dataArgs.keys():
            genome = dataArgs["genome1"]
        else:
            if PHATE_WARNINGS:
                print("genomics_compareGenomes says, WARNING: Expected genome1 name in addParalog2genome")
                return
        for genome_obj in self.genomeList:
            if genome_obj.name == genome:
                genome_obj.addParalog(dataArgs)
                break
        return

    # Method getGeneCallString extracts the genecall name from the annotation string
    def getGeneCallString(self,inString):  
        inList = ast.literal_eval(inString) # Convert string representation of a list to an actual list
        geneCallString = inList[0]          # First element of the list is the genecall string
        return geneCallString

    def addHit2genome(self,dataArgs): 
        # This method inserts a new gene hit into a genome's geneList or proteinList, or records a gene as a loner
        # with respect to another genome. Note that every gene is assumed a loner until proven otherwise. Any mutual
        # or singular hit to a gene/protein of another genome nullifies that gene's status as a loner.

        # First, create gene or protein object
        hitFlavor = "gene"; GENE = False; PROTEIN = False
        gene1id = ""; gene2id = ""; protein1id = ""; protein2id = ""
        gene_obj = None; protein_obj = None   # a gene_protein object (gene or protein template)

        # Create gene_protein object, according to flavor
        if "hitFlavor" in dataArgs.keys():
            hitFlavor = dataArgs["hitFlavor"]
        else:
            if PHATE_WARNINGS:
                print("genomics_compareGenomes says, WARNING: hitFlavor not specified")
                return
        if hitFlavor == "gene":
            gene_obj = self.geneTemplate
            GENE = True
        elif hitFlavor == "protein":
            protein_obj = self.proteinTemplate 
            PROTEIN = True
        else:
            if PHATE_WARNINGS:
                print("genomics_compareGenomes says, WARNING: Unrecognized hitFlavor, ",dataArgs["hitFlavor"])
                return

        GENOME_ONE = False; GENOME_TWO = False # Should exist data for both genomes if mutual or singular hit; one if loner
        # Data needed for "mutual" or "singular" hit entry
        # Determine which genome's hit to process, or both.
        # Find the two genome objects to which mutual hits will be added
        # Compute unique identifiers for query and subject genes 

        # Determine type of hit and whether the query is genome1 versus genome2
        match_mutual   = re.search("mutual",  dataArgs["hitType"])
        match_singular = re.search("singular",dataArgs["hitType"])
        match_loner    = re.search("loner",   dataArgs["hitType"])
        match_query    = re.search("\d",      dataArgs["hitType"])

        if GENE:
            if dataArgs["gene1"] != "":
                GENOME_ONE = True
                genome1_obj = self.findGenomeObject(dataArgs["genome1"])
                gene1id = dataArgs["genome1"] + ':' + dataArgs["contig1"] + ':' + dataArgs["gene1"]
            if dataArgs["gene2"] != "":
                GENOME_TWO = True
                genome2_obj = self.findGenomeObject(dataArgs["genome2"])
                gene2id = dataArgs["genome2"] + ':' + dataArgs["contig2"] + ':' + dataArgs["gene2"]
        elif PROTEIN:
            if dataArgs["protein1"] != "":
                GENOME_ONE = True
                genome1_obj = self.findGenomeObject(dataArgs["genome1"])
                protein1id = dataArgs["genome1"] + ':' + dataArgs["contig1"] + ':' + dataArgs["protein1"]
            if dataArgs["protein2"] != "":
                GENOME_TWO = True
                genome2_obj = self.findGenomeObject(dataArgs["genome2"])
                protein2id = dataArgs["genome2"] + ':' + dataArgs["contig2"] + ':' + dataArgs["protein2"]

        if GENOME_ONE:
            # Search for query gene in genome1 (if exists)
            GENE_FOUND = False; PROTEIN_FOUND = False; NEW = False
            if GENE:
                for gene_obj in genome1_obj.geneList:
                    if gene_obj.contigName == dataArgs["contig1"] and gene_obj.name == dataArgs["gene1"]:
                        GENE_FOUND = True
                        break
                if not GENE_FOUND: 
                    # Create and populate a new gene object
                    NEW = True
                    gene_obj = copy.deepcopy(self.geneTemplate)
                    gene_obj.name         = dataArgs["gene1"]
                    gene_obj.type         = "gene"
                    gene_obj.identifier   = gene1id 
                    gene_obj.cgpHeader    = dataArgs["gene1"]
                    geneCallFields        = dataArgs["gene1"].split('/')   # format: cds#/strand/start/stop/
                    (cds,geneNumber)      = geneCallFields[0].split('cds')
                    gene_obj.number       = geneNumber
                    gene_obj.parentGenome = dataArgs["genome1"]
                    gene_obj.contigName   = dataArgs["contig1"]
                    gene_obj.annotation   = dataArgs["annotations1"] 
                # Add hit
                if match_mutual:
                    gene_obj.mutualBestHitList.append(gene2id) 
                    gene_obj.isLoner = False
                if match_singular and match_query.group(0) == '1':
                    gene_obj.singularBestHitList.append(gene2id)
                    gene_obj.isLoner = False
                if match_loner and match_query.group(0) == '1':
                    gene_obj.lonerList.append(genome1_obj.name)   # To record a loner, append the name of the genome that this gene is a loner wrt
                # If this gene object needed to be newly created, then add to geneList; else it's already there!
                if NEW:
                    genome1_obj.geneList.append(gene_obj)
            elif PROTEIN:
                for protein_obj in genome1_obj.proteinList:
                    if protein_obj.contigName == dataArgs["contig1"] and protein_obj.name == dataArgs["protein1"]:
                        PROTEIN_FOUND = True
                        break
                if not PROTEIN_FOUND: 
                    # Create and populate a new gene object
                    NEW = True
                    protein_obj = copy.deepcopy(self.proteinTemplate)
                    protein_obj.name         = dataArgs["protein1"]
                    protein_obj.type         = "protein"
                    protein_obj.identifier   = protein1id 
                    protein_obj.cgpHeader    = dataArgs["protein1"]
                    proteinNameFields        = dataArgs["protein1"].split('/')  # format: cds#/strand/start/stop/
                    (cds,proteinNumber)      = proteinNameFields[0].split('cds')
                    protein_obj.number       = proteinNumber
                    protein_obj.parentGenome = dataArgs["genome1"]
                    protein_obj.contigName   = dataArgs["contig1"]
                    protein_obj.annotation   = dataArgs["annotations1"] 
                # Add hit
                if match_mutual:
                    protein_obj.mutualBestHitList.append(gene2id) 
                    protein_obj.isLoner = False
                if match_singular and match_query.group(0) == '1':
                    protein_obj.singularBestHitList.append(protein2id)
                    protein_obj.isLoner = False
                if match_loner and match_query.group(0) == '1':
                    protein_obj.lonerList.append(genome1_obj.name)
                # If this protein object needed to be newly created, then add to proteinList; else it's already there!
                if NEW:
                    genome1_obj.proteinList.append(protein_obj)

        if GENOME_TWO:
            # Search for query gene in genome2 (if exists)
            GENE_FOUND = False; PROTEIN_FOUND = False; NEW = False
            if GENE:
                for geneObj in genome2_obj.geneList:
                    if geneObj.contigName == dataArgs["contig2"] and geneObj.name == dataArgs["gene2"]:
                        GENE_FOUND = True
                        break
                if not GENE_FOUND: 
                    # Create and populate a new gene object
                    NEW = True
                    gene_obj = copy.deepcopy(self.geneTemplate)
                    gene_obj.name         = dataArgs["gene2"]
                    gene_obj.type         = "gene"
                    gene_obj.identifier   = gene2id 
                    gene_obj.cgpHeader    = dataArgs["gene2"]
                    geneNameFields        = dataArgs["gene2"].split('/')
                    (cds,geneNumber)      = geneNameFields[0].split('cds')
                    gene_obj.number       = geneNumber
                    gene_obj.parentGenome = dataArgs["genome2"]
                    gene_obj.contigName   = dataArgs["contig2"]
                    gene_obj.annotation   = dataArgs["annotations2"] 
                # Add hit
                if match_mutual:
                    gene_obj.mutualBestHitList.append(gene1id) 
                    gene_obj.isLoner = False
                if match_singular and match_query.group(0) == '2':
                    gene_obj.singularBestHitList.append(gene1id)
                    gene_obj.isLoner = False
                if match_loner and match_query.group(0) == '2':
                    gene_obj.lonerList.append(dataArgs["genome1"])
                if NEW:
                    genome2_obj.geneList.append(gene_obj)
            elif PROTEIN:
                for proteinObj in genome2_obj.proteinList:
                    if proteinObj.contigName == dataArgs["contig2"] and proteinObj.name == dataArgs["protein2"]:
                        PROTEIN_FOUND = True
                        break
                if not PROTEIN_FOUND: 
                    # Create and populate a new gene object
                    NEW = True
                    protein_obj = copy.deepcopy(self.proteinTemplate)
                    protein_obj.name         = dataArgs["protein2"]
                    protein_obj.type         = "protein"
                    protein_obj.identifier   = protein2id 
                    protein_obj.cgpHeader    = dataArgs["protein2"]
                    proteinNameFields        = dataArgs["protein2"].split('/')
                    (cds,proteinNumber)      = proteinNameFields[0].split('cds')
                    protein_obj.number       = proteinNumber
                    protein_obj.parentGenome = dataArgs["genome2"]
                    protein_obj.contigName   = dataArgs["contig2"]
                    protein_obj.annotation   = dataArgs["annotations2"] 
                # Add hit
                if match_mutual:
                    protein_obj.mutualBestHitList.append(protein1id) 
                    protein_obj.isLoner = False
                if match_singular and match_query.group(0) == '2':
                    protein_obj.singularBestHitList.append(protein1id)
                    protein_obj.isLoner = False
                if match_loner and match_query.group(0) == '2':
                    protein_obj.lonerList.append(dataArgs["genome1"])
                if NEW:
                    genome2_obj.proteinList.append(protein_obj)
        return

    def findGenomeObject(self,genomeName):
        for genome_object in self.genomeList:
            if genome_object.name == genomeName:
                return genome_object
        return

    #===== COMPARISON GENOMIC METHODS

    def computeHomologyGroups(self):
        # Compute homology groups
        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Homology group computation complete.")
        return

    # For each gene/protein in reference genome, write correspondence set to file
    def saveHomologyGroups(self):
        for genome in self.genomeList:
            if genome.isReference:
                for gene in genome.geneList:
                    pass
                for protein in genome.proteinList:
                    pass

        if PHATE_PROGRESS:
            print("genomics_compareGenomes says, Homology groups have been written to files.")
        return

    #===== COMPARISON DATA CHECK METHODS

    def countGenomes(self):
        self.genomeCount = len(self.genomeList)
        if PHATE_MESSAGES:
            print("genomics_compareGenomes says, There are",self.genomeCount,"genomes.")
        if DEBUG:
            print("genomics_compareGenomes says, DEBUG: There are",self.genomeCount,"genomes.")
        return

    def checkMutualBestHitList(self):
        genomeCount = len(self.genomeList)
        for genome in self.genomeList:
            genome.checkMutualBestHitList(genomeCount)
        return

    def checkUnique(self):
        tempList = []
        for genome in genomeList:
            if genome.name in tempList:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes genomes obj says, WARNING: ",genome.name," occurs more than once in genomes object.")
            else:
                tempList.append(genome.name)
        return

    #===== COMPARISON PRINT METHODS

    def writeCorrespondences(self):
        for genome in self.genomeList:
            if genome.isReference:
                print("********** GENE CORRESPONDENCES **********")
                # For each reference gene, print non-redundant list of mutual or singular best hit wrt each other genome
                for gene in genome.geneList:
                    correspondenceList = []
                    print("Genes corresponding to",gene.identifier)
                    for hit in gene.mutualBestHitList:
                        if hit not in correspondenceList:
                            correspondenceList.append(hit)
                    for hit in gene.singularBestHitList:
                        if hit not in correspondenceList:
                            correspondenceList.append(hit)
                    for hit in correspondenceList:
                        print("  ",hit)
                print("********** End Gene Correspondences")
        return

    def writeCoreGenome(self):
        genomeCount = len(self.genomeList)
        count = 0
        for genome in self.genomeList:
            if genome.isReference:
                print("********** CORE GENOME **********")
                # For each reference gene that matches genes in all other genomes, list the gene set
                for gene in genome.geneList:
                    if len(gene.mutualBestHitList) == genomeCount-1:
                        count += 1
                        print("Gene Set #",count,':')
                        print(gene.identifier)
                        for hit in gene.mutualBestHitList:
                            print(hit)
                print("********** End Core Genome **********")
        return

    def writeMutualBestHitList(self):
        for genome in self.genomeList:
            if genome.isReference:
                print("************** ",genome.name," **************")
                print("************** Mutual Best Hits ")
                for gene in genome.geneList:
                    print("** gene ",gene.identifier)
                    gene.writeMutualBestHitList()
                print("************** End of Mutual Best Hits List ")
        return

    def writeSingularBestHitList(self):
        for genome in self.genomeList:
            if genome.isReference:
                print("************** ",genome.name," **************")
                print("************** Singular Best Hits ")
                for gene in genome.geneList:
                    print("** gene ",gene.identifier)
                    gene.writeSingularBestHitList()
                print("************** End of Singular Best Hits List ")
        return

    def writeGeneCorrespondences(self):
        runningList = []
        for genome in self.genomeList:
            if genome.isReference:
                print("********** ",genome.name," **********")
                for gene in self.geneList:
                    for hit in self.mutualBestHitList:
                        if hit not in runningList:
                            runningList.append(hit)
                    for hit in self.singularBestHitList:
                        if hit not in runningList:
                            runningList.append(hit)
                    print("genes corresponding to",gene.identifier,':')
                    for hit in runningList:
                        print("     ",hit)
                print("********** End of gene correspondences ")
        return

    def writeLonerList(self):
        for genome in self.genomeList:
            if genome.isReference:
                print("********** ",genome.name," **********")
                print("********** Loners ")
                for gene in genome.geneList:
                    if gene.isLoner:
                        print(gene.identifier)
                print("********** End of loner list ")
        return

    def printReport(self):
        self.writeMutualBestHitList()
        self.writeSingularBestHitList()
        self.writeLonerList()
        self.writeCoreGenome()
        self.writeCorrespondences()
        return

    def printAll(self):
        print("=========Genome Set=============")
        print("name:",self.name)
        print("referenceGenome:",self.referenceGenome)
        print("genomeCount:",self.genomeCount)
        print("Set of genomes:")
        for genome in self.genomeList:
            genome.printAll()
        print("=========End Genome Set=========")
        return

#############################################################################################################
# Class genome stores metadata 
#############################################################################################################
class genome(object):

    def __init__(self):
        self.name                 = ""     # Name of this genome (e.g., Lambda)
        self.species              = ""     # Species name for this genome (e.g., Ecoli_Lambda_phage)
        self.isReference          = False  # True if designated a reference genome
        self.contigList           = []     # Set of contig names (fasta headers)
        self.geneList             = []     # List of gene_protein objects 
        self.proteinList          = []     # List of gene_protein objects 
        self.paralogList          = []     # List of paralogSet objects

    def addParalog(self,dataArgs):
        hitType = ""; gene1 = ""; gene2 = ""; protein1 = ""; protein2 = ""
        geneCall1 = ""; geneCall2 = ""

        # Read input parameters; not all these are being used just yet
        if "hitType" in dataArgs.keys():
            hitType = dataArgs["hitType"]
        if re.search('gene',hitType):
            if "gene1" in dataArgs.keys():
                gene1 = dataArgs["gene1"]
            if "gene2" in dataArgs.keys():
                gene2 = dataArgs["gene2"]
        elif re.search('protein',hitType):
            if "protein1" in dataArgs.keys():
                protein1 = dataArgs["protein1"]
            if "protein2" in dataArgs.keys():
                protein2 = dataArgs["protein2"]
        if "contig1" in dataArgs.keys():
            contig1 = dataArgs["contig1"]
        if "contig2" in dataArgs.keys():
            contig2 = dataArgs["contig2"]
        if "geneCall1" in dataArgs.keys():
            geneCall1 = dataArgs["geneCall1"]
        if "geneCall2" in dataArgs.keys():
            geneCall2 = dataArgs["geneCall2"]
        if "annotation1" in dataArgs.keys():
            annotation1 = dataArgs["annotation1"]
        if "annotation2" in dataArgs.keys():
            annotation2 = dataArgs["annotation2"]

        # Find gene1 and gene2 in genome; get gene identifiers
        for gene_obj1 in self.geneList:
            if gene_obj1.cgpHeader == gene1:
                for gene_obj2 in self.geneList:
                    if gene_obj2.cgpHeader == gene2:
                        paralogID = gene_obj2.identifier
                        if paralogID not in gene_obj1.paralogList:
                            gene_obj1.paralogList.append(paralogID)
                            break
        return

    #===== GENOME DATA CHECK METHODS

    def checkMutualBestHitList(self,genomeCount):
        for gene in self.geneList:
            if len(gene.mutualBestHitList) != genomeCount-1:
                if PRINT_WARNINGS:
                    print("genomics_compareGenomes says, WARNING: mutualBestHitList for gene",gene.identifier,"incorrect")
                    print("   ",gene.mutualBestHitList)
        return

    def checkUnique(self):
        tempList = []
        for gene in self.geneList:
            if gene.identifier in tempList:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes genome obj says, WARNING: ",gene.identifier," is not unique")
            else:
                tempList.append(gene.identifier)
            
        tempList = []
        for gene in self.geneList:
            if gene.cgpHeader in tempList:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes genome obj says, WARNING: ",gene.cgpHeader," is not unique")
            else:
                tempList.append(gene.cgpHeader)
            
        tempList = []
        for protein in self.proteinList:
            if protein.identifier in tempList:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes genome obj says, WARNING: ",protein.identifier," is not unique")
            else:
                tempList.append(protein.identifier)

        tempList = []
        for protein in self.proteinList:
            if protein.cgpHeader in tempList:
                if PHATE_WARNINGS:
                    print("genomics_compareGenomes genome obj says, WARNING: ",protein.cgpHeader," is not unique")
            else:
                tempList.append(protein.cgpHeader)
        return

    #===== GENOME PRINT METHODS

    def printReport(self):
        return

    def printAll(self):
        print("=========Genome========")
        print("name:",self.name)
        print("species:",self.species)
        print("isReference:",self.isReference)
        print("contigs:",)
        if self.contigList:
            for contig in self.contigList:
                print(contig)
        else:
            print("There are no contigs.")
        if self.geneList:
            for gene in self.geneList:
                gene.printAll()
        else:
            print("There are no genes.")
        if self.proteinList:
            for protein in self.proteinList:
                protein.printAll()
        else:
            print("There are no proteins.")
        if self.paralogList:
            for paralogSet in self.paralogList:
                paralogSet.printAll()
        else:
            print("There are no paralogs")
        print("=========End Genome====")
        return

#####################################################################################################
# Class paralog organizes genes and proteins within a given genome that are considered paralogs.
class paralogSet(object):
    
    def __init__(self):
        self.paralogType          = "unknown" # "gene" or "protein"
        self.paralogList          = []        # List of either gene or protein unique identifiers
        self.setSize              = 0         # number of paralogs in this set

    def countParalogs(self):
        self.setSize = len(self.paralogList)
        if PHATE_MESSAGES:
            print("genomics_compareGenomes says, There are",self.setSize,"paralogs")
        return

    #===== PARALOG PRINT METHODS

    def printReport(self):
        return

    def printAll(self):
        print("paralogType:",self.paralogType)
        print("setSize:",self.setSize)
        print("paralogList:",self.paralogList)
        return

######################################################################################################
# Class gene_protein stores meta-data about a gene or protein.
class gene_protein(object):

    def __init__(self):
        self.type                 = "gene"    # "gene" or "protein"
        self.name                 = ""        # Ex: "phanotate_5"
        self.identifier           = ""        # Unique: genome + contig + name
        self.cgpHeader            = ""        # CGP-assigned header; Ex: cgp5/+/72/485/
        self.number               = 0         # Unique: Set to correspond to protein 
        self.parentGenome         = ""        # Ex: "Lambda" - corresponds to a genome object's name
        self.contigName           = ""        # Ex: "Lambda_contig_1"; read from CGP report
        self.annotation           = ""        # The full annotation string, read from CGP report 
        self.isLoner              = True      # True if this gene has no correspondences
        self.mutualBestHitList    = []        # list of gene identifiers that are mutual best hits, across genomes
        self.singularBestHitList  = []        # list of gene identifiers that are best hits, relative to this gene, across genomes
        self.correspondenceList   = []        # List of corresponding genes (mutual or best-hit) across genomes: list of gene identifiers 
        self.lonerList            = []        # List of the genome names that this gene/protein is a loner with respect to
        self.groupList            = []        # list of all corresponding genes plus paralogs
        self.paralogList          = []        # List of paralogs within its own parent genome: list of gene identifiers <data is redundant; should pull paralog list as list of lists at genome level.

    def addMutualBestHit(self,hit):
        self.mutualBestHistList.append(hit)
        return

    def addSingularBestHit(self,hit):
        self.singularBestHitList.append(hit)
        return

    def addGroupMember(self,member):
        self.groupList.append(member)

    # Construct a set of genes/proteins that are related by homology
    def constructGroup(self):
        # self.groupList

        if PHATE_MESSAGES:
            print("genomics_compareGenomes says, Group constructed for gene_protein",self.identifier,";",self.type)
        return

    #===== GENE_PROTEIN DATA CHECK METHODS

    # For development purposes
    def verifyLoner(self):
        if self.mutualBestHitList:
            if PHATE_WARNINGS:
                print("genomics_compareGenomes says, Not a loner due to mutual best hit:",self.identifier,";",self.type)
            return False
        if self.singularBestHistList:
            if PHATE_WARNINGS:
                print("genomics_compareGenomes says, Not a loner due to singular best hit:",self.identifier,";",self.type)
            return False
        return True

    #===== GENE_PROTEIN PRINT METHODS

    def writeMutualBestHitList(self):
        for hit in self.mutualBestHitList:
            print(hit)
        return

    def writeSingularBestHitList(self):
        for hit in self.singularBestHitList:
            print(hit)
        return

    def writeLonerList(self):
        for genome in self.lonerList:
            print(genome)
        return

    def printReport(self):
        return

    # For development purposes
    def printAll(self):
        print("===type:",self.type)
        print("name:",self.name)
        print("identifier:",self.identifier)
        print("cgpHeader:",self.cgpHeader)
        print("number:",self.number)
        print("parentGenome:",self.parentGenome)
        print("contigName:",self.contigName)
        print("annotation:",self.annotation)
        print("isLoner:",self.isLoner)
        print("mutualBestHitList:",self.mutualBestHitList)
        print("singularBestHitList:",self.singularBestHitList)
        print("correspondenceList:",self.correspondenceList)
        print("paralogList:",self.paralogList)
        print("===")
        return
