# Auto-Lapse-New-Interval
# Anki 2.1 plugin
# Author: EJS, daeds1dog
# Version 0.1
# License: GNU GPL v3 <www.gnu.org/licenses/gpl.html>
from __future__ import division
import datetime, time, math, json, os
from anki.hooks import wrap, addHook
from aqt import *
from aqt.main import AnkiQt
from anki.utils import intTime

# Addon config
config = mw.addonManager.getConfig(__name__)

card_sample_size = config.get('card_sample_size', 100)
defaultTSR = config.get('target_success_rate', 85)
change_silently = config.get('change_silently', False)
ignore_silently = config.get('ignore_silently', True)


# ------------Nothing to edit below--------------------------------#
rev_lapses = {}

# CONFIG file to store last time options settings were adjusted
previous = {} # Record of previous adjustment dates
LapseConffile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "autoLapseNewInterval.data")
# NB The line below may not work with Anki 2.1
# Try commenting it out if you get errors.
#LapseConffile = LapseConffile.decode(sys.getfilesystemencoding())
if os.path.exists(LapseConffile):
    previous = json.load(open(LapseConffile, 'r'))


def save_lapseStats():
    json.dump(previous, open(LapseConffile, 'w'))


# Find settings group ID
def find_settings_group_id(name):
    dconfs = mw.col.decks.all_config()
    for dconf in dconfs:
        if dconf['name'] == name:
            return dconf['id']
    return False


# Find decks in settings group
def find_decks_in_settings_group(group_id):
    members = []
    decks = mw.col.decks.get_all_legacy()
    for d in decks:
        if 'conf' in d and int(d['conf']) == int(group_id):
            members.append(d['id'])
    return members




# NOTE:
# from anki.utils import intTime
# intTime function returns seconds since epoch UTC multipiled by an optional scaling parameter; defaults to 1.


# Main Function
def adjLapse_all(silent=True):
    eval_lapsed_newIvl(silent)


# Startup Function
def adjLapse_startup():
    global previous
    profile = aqt.mw.pm.name
    if profile not in previous:
        previous[profile] = {}
    adjLapse_all(True) # Includes functions below

#Run when profile is loaded, save stats when unloaded
addHook("profileLoaded", adjLapse_startup)
addHook("unloadProfile", save_lapseStats)


#Find the success rate for a deck
def deck_lapsed_success_rate(deck_ids, lapsed_rev_records, from_date):
    lapsed_query = """select count() from
              (select a.id, a.ease
              from revlog as a, cards as c
              where
			  a.id > %s
              and a.type = 1
              and a.ease > 1
              and a.cid = c.id
              and (""" % from_date
    i = 0
    for d in deck_ids:
        if i == 0:
            lapsed_query += "c.did = %s" % d
            i = 1
        else:
            lapsed_query += " or c.did = %s" % d
    lapsed_query += """)
            group by a.id
            order by a.id)"""
    lapsed_successes = mw.col.db.scalar(lapsed_query)

    lapsed_success_rate = int(100 * lapsed_successes / (lapsed_rev_records + lapsed_successes))
    return lapsed_success_rate

#Find number of lapsed review records in deck
def lapsed_records_in_deck(deck_id, from_date):
    lapsed_query = """select count() from
            (select a.id, a.ease
            from revlog as a, cards as c
            where
            a.id > %s
            and a.type = 1
            and a.ease = 1
            and a.cid = c.id
            and c.did = %s
            group by a.id
            order by a.id)""" % (from_date, deck_id)
    lapsed_records = mw.col.db.scalar(lapsed_query)
    if lapsed_records:
        return lapsed_records
    else:
        return 0

# Calculate the Lapse success rate of an options group
def og_lapsed_success_rate(name, min_look_back):
    profile = aqt.mw.pm.name
    creation_date = (int(mw.col.crt) * 1000)
    deck_ids = []
    lapsed_rev_records = 0
    group_id = find_settings_group_id(name)
        #add profile to previous dates dictionary
    if 'lapsed' not in previous[profile][name]:
        previous[profile][name]['lapsed'] = creation_date
    from_date = previous[profile][name]['lapsed']
    #exit if it has been less than 24 hours since last adjustment
    cur_date = intTime(1000)
    #if (cur_date - from_date) < (24 * 60 * 60 * 1000):
    #    #utils.showInfo("Waiting 24 hours to adjust Lapse Next Interval for %s." % name)
    #    return False, False
    if group_id:
        # Find decks and cycle through
        decks = find_decks_in_settings_group(group_id)
        #utils.showInfo("Will now calculate total lapsed cards for %s." % name)
        for d in decks:
            deck_ids.append(d)
            lapsed_rev_records += lapsed_records_in_deck(d, from_date)
        # make sure we have enough records in review to
        if lapsed_rev_records >= min_look_back:
            lapsed_success_rate = deck_lapsed_success_rate(deck_ids, lapsed_rev_records, from_date) #look back over all records since last adjustment
        else:
            lapsed_success_rate = False
        return lapsed_success_rate, lapsed_rev_records
    else:
        return False, False

#Adjust the lapsed new interval setting for an options group
def adj_lapsed_newIvl(group_id, silent=True):
    global previous
    profile = aqt.mw.pm.name
    tsr = defaultTSR
    # Return if target success rate is false or 0.
    if not tsr: return
    #find name of group
    dconf = mw.col.decks.get_config(group_id)
    name = dconf['name']
    if name not in previous[profile]:
        previous[profile][name] = {}
    cur_LNIvl = float(dconf['lapse']['mult'])
    lapsed_success_rate, lapsed_rev_records = og_lapsed_success_rate(name, card_sample_size)
    # Returns False, False if we don't have enough review records since last time.
    if lapsed_success_rate and lapsed_rev_records and lapsed_success_rate != tsr:
        target_rate = float(tsr) / 100
        cur_rate = float(lapsed_success_rate) / 100
        #Simplistic ratio adjustment
        new_LNIvl = round(cur_LNIvl * cur_rate/target_rate, 2)
        if new_LNIvl > 1:
            new_LNIvl = 1
        if change_silently or utils.askUser("%s"
                "\n\nLapsed Card Success Rate: %s"
                "\nTarget Success Rate: %s"
                "\nCurrent lapsed new interval: %s"
                "\nSuggested interval: %s"
                "\n\nAccept new Lapsed new interval?" % (
                name, cur_rate, target_rate, cur_LNIvl, new_LNIvl)):
            # make changes
            dconf['lapse']['mult'] = new_LNIvl
            mw.col.decks.setConf(dconf, group_id)
            previous[profile][name]['lapsed'] = intTime(1000)
            #utils.showInfo("Updating lapsed new interval currently disabled")
    else:
        if not change_silently and not ignore_silently:
            utils.showInfo("Lapsed New Interval\n\nNot enough records for options group %s (%d)" % (name, lapsed_rev_records))


def eval_lapsed_newIvl(silent=False):
    #find all deck options groups
    dconfs = mw.col.decks.all_config()
    for dconf in dconfs:
        adj_lapsed_newIvl(dconf['id'], silent)
