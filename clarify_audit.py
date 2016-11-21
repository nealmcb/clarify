#!/usr/bin/env python
"""
Clarify_Audit
~~~~~~~~

Intro Comment for clarify_audit.

%InsertOptionParserUsage%

Example:
 ./clarify_audit.py -d 10 detail.xml

Todo:
   Provide a parameter for outlier threshold
   Classify all negative values for turnout or residual votes as outliers

"""

import os
import sys
import logging
from optparse import OptionParser
from datetime import datetime
import clarify
import itertools
import numpy as np

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__version__ = "0.1.0"
__date__ = "2016-11-20"
__copyright__ = "Copyright (c) 2016 Neal McBurnett"
__license__ = "LGPL v3"

parser = OptionParser(prog="clarify_audit.py", version=__version__, usage="usage: %prog [options] detail.xml")

parser.add_option("-d", "--debuglevel",
  type="int", default=logging.WARNING,
  help="Set logging level to debuglevel: DEBUG=10, INFO=20,\n WARNING=30 (the default), ERROR=40, CRITICAL=50")

# incorporate OptionParser usage documentation in our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())

def is_outlier(points, thresh=3.5):
    """
    From Joe Kington: http://stackoverflow.com/a/22357811/507544
    
    Returns a boolean array with True if points are outliers and False 
    otherwise.

    Parameters:
    -----------
        points : An numobservations by numdimensions array of observations
        thresh : The modified z-score to use as a threshold. Observations with
            a modified z-score (based on the median absolute deviation) greater
            than this value will be classified as outliers.

    Returns:
    --------
        mask : A numobservations-length boolean array.

    References:
    ----------
        Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
        Handle Outliers", The ASQC Basic References in Quality Control:
        Statistical Techniques, Edward F. Mykytka, Ph.D., Editor. 
    """

    if len(points.shape) == 1:
        points = points[:,None]
    median = np.median(points, axis=0)
    diff = np.sum((points - median)**2, axis=-1)
    diff = np.sqrt(diff)
    med_abs_deviation = np.median(diff)

    modified_z_score = 0.6745 * diff / med_abs_deviation

    return modified_z_score > thresh

def select_outliers(pointlist, pointvalues, thresh=3.5): # really about 3.5):
    "Given a list of rows and a corresponding list of values, identify outliers and return the matching rows"

    points = np.array(pointvalues)
    selections = is_outlier(points, thresh)
    return(list(itertools.compress(pointlist, selections)))

def rollupChoice(results, contest, choice, jurisdiction):
    "Return the sum of votes for the given jurisdiction, contest and choice"

    return(sum(r.votes for r in results if r.contest == contest and r.choice == choice and r.jurisdiction == jurisdiction))

def rollupContest(results, contest, jurisdiction):
    """Return the residual rate, residual votes, sum of votes and total ballots
    for the given jurisdiction and contest"""

    choice_votes = sum(rollupChoice(results, contest, choice, jurisdiction) for choice in contest.choices)
    ballots = jurisdiction.ballots_cast
    residual_votes = ballots - choice_votes
    return((residual_votes * 100.0 / ballots, residual_votes, choice_votes, ballots))

def clarify_audit(xmlfile):
    "Process the xmlfile representing Clarify data and identify some outliers for residual vote rate and turnout"

    p = clarify.Parser()
    p.parse(xmlfile)

    # Once the parse() method has been called, the Parser object has properties that provide information about the election and jurisdiction of the results file:

    print "Report for %s %s %s\n%s\n" % (p.region, p.election_name, p.election_date, xmlfile)

    # Print list of contests sorted by number of counties participating in them
    for v in sorted([(c.counties_participating, c.text) for c in p.contests], reverse=True):
        logging.info(v)

    # calculate turnout rates, and identify outliers
    turnouts = sorted([(j.ballots_cast * 100.0 / j.total_voters, j.ballots_cast, j.total_voters, j.name) for j in p.result_jurisdictions])

    turnoutOuts = select_outliers(turnouts, [t[0] for t in turnouts])
    print "Outliers for turnout percentage"
    print "%TOut\tBallots\tReg\tCounty"

    for out in turnoutOuts:
        print "%.1f%%\t%d\t%d\t%s" % (out[0], out[1], out[2], out[3])

    results = p.results

    numberJurisdictions = len(p.result_jurisdictions)

    print "\nOutliers for residual vote within each state-wide contest"

    # For each contest, look at residual vote rates across the counties,
    # and identify residual vote rates that are outliers compared to other counties
    for contest in p.contests:
        # Don't have a good way to do residual vote rate for non-state-wide contests
        if contest.counties_participating == numberJurisdictions:

            byResidual = sorted([(rollupContest(results, contest, j), j.name)
                                 for j in p.result_jurisdictions]) # FIXME or participating?
            out = select_outliers(byResidual, [e[0][0] for e in byResidual])
            print("%s:" % (contest,))
            print("\tResid%\tResid\tVotes\tBallots\tCounty")
            
            for i in out:
                print("\t%.1f%%\t%d\t%d\t%d\t%s" % (i[0][0], i[0][1], i[0][2], i[0][3], i[1]))

def main(parser):
    "Run clarify_audit with given OptionParser arguments"

    (options, args) = parser.parse_args()

    #configure the root logger.  Without filename, default is StreamHandler with output to stderr. Default level is WARNING
    logging.basicConfig(level=options.debuglevel)   # ..., format='%(message)s', filename= "/file/to/log/to", filemode='w' )

    logging.debug("options: %s; args: %s", options, args)

    if len(args) != 1:
        logging.error("Must specify one xml file.\noptions: %s; args: %s", options, args)
        parser.print_help()
        sys.exit(1)

    clarify_audit(args[0])

if __name__ == "__main__":
    main(parser)
