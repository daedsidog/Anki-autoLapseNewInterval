## In a nutshell

The code below will loop through each of your deck options groups, find the success rate for post-lapse reviews, and attempt to adjust the _Lapse New Interval_ percentage to hit an 85% average success rate.

## Background

Previously, I wrote about using efficient settings for the new interval after a lapse.

See: [New Interval After a Lapse in Anki](https://eshapard.github.io/anki/anki-new-interval-after-a-lapse.html)

> In deck settings set the _New Interval_ under the _Lapses_ tab to make the new interval of forgotten cards a percentage of their previous interval. Ideally, play with this percentage until you have an 80-90% success rate on re-learned cards.

I mentioned that I had some code to automate this, but I’d have to separate it from a bunch of other code in a big messy addon I made.

Well, I finally got around to doing that.

## Details

*   Adjustments only happen on profile load (startup).
*   You are prompted to accept changes or not.
*   Deck options groups with a _Lapse New Interval_ setting of 0 (the default) will remain unchanged.
*   Currently, all decks get the 85% target; you can’t set individual targets for different options groups, but that would be a pretty easy change to make (I may do it later).
*   No changes are made unless a minimum of new reviews are found (set to 100; configurable).
*   We keep track of the last time we changed a setting for each options group and then only make changes when we have 100 more reviews to analyse.
*   On first run, we analyze all post-lapse reviews; after that we look just at the last 100.

### Adjustment Algorithm

If your current success rate is 20% higher, than the target rate (85%), we make the _Lapse New Interval_ 20% longer; if our success rate is 20% lower, we make the _Lapse New Interval_ 20% shorter… simple, but should work OK.

## The Code

N.B. I won’t be posting this code to ankiweb any time soon. This is very bare-bones and not very user-friendly and I don’t feel like putting in the work to make it idiot-proof… I mean user-friendly enough for noobs.

Save this code as `autoLapseNewInterval.py` or something like that in your Anki addons directory.

UPDATE 2018-12-29: I’ve had a report of this working in Anki 2.1\. You’ll need to save the file as `__init__.py` in a directory called autoLapseNewInterval in your Anki 2.1 addons directory and possibly comment out one of the lines in the code (see comments within code below).


    # Auto-Lapse-New-Interval
    # Anki 2 plugin
    # Author: EJS
    # Version 0.1
    # License: GNU GPL v3 <www.gnu.org/licenses/gpl.html>
    from __future__ import division
    import datetime, time, math, json, os
    from anki.hooks import wrap, addHook
    from aqt import *
    from aqt.main import AnkiQt
    from anki.utils import intTime

    # card_sample_size
    # Number of cards needed for adequate sample size
    #    we won't update settings
    #    unless we have at least this many cards 
    #    to go off of. This prevents us from changing initial 
    #    settings based on a small set of data.
    card_sample_size = 100
    defaultTSR = 85 #Default target success rate (as a percentage)

    # ------------Nothing to edit below--------------------------------#
    rev_lapses = {}

    # CONFIG file to store last time options settings were adjusted
    previous = {} # Record of previous adjustment dates
    LapseConffile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "autoLapseNewInterval.data")
    # NB The line below may not work with Anki 2.1
    # Try commenting it out if you get errors.
    LapseConffile = LapseConffile.decode(sys.getfilesystemencoding())
    if os.path.exists(LapseConffile):
        previous = json.load(open(LapseConffile, 'r'))

    def save_lapseStats():
        json.dump(previous, open(LapseConffile, 'w'))

    # Find settings group ID
    def find_settings_group_id(name):
        dconf = mw.col.decks.dconf
        for k in dconf:
            if dconf[k]['name'] == name:
                return k
        return False

    # Find decks in settings group
    def find_decks_in_settings_group(group_id):
        members = []
        decks = mw.col.decks.decks
        for d in decks:
            if 'conf' in decks[d] and int(decks[d]['conf']) == int(group_id):
                members.append(d)
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
    def deck_lapsed_success_rate(deck_ids, lapsed_rev_records):
        lapsed_query = """select count() from
                  (select * from 
                  (select min(b.id) as bid, a.id as aid, a.ivl, a.lastIvl as aLastIvl, b.ivl as bIvl, b.lastIvl as bLastIvl, b.ease
                  from revlog as a, revlog as b, cards as c
                  where
                  a.type = 1
                  and a.ease = 1
                  and a.cid = b.cid
                  and a.cid = c.id
                  and ("""
        i = 0
        for d in deck_ids:
            if i == 0:
                lapsed_query += "c.did = %s" % d
                i = 1
            else:
                lapsed_query += " or c.did = %s" % d
        lapsed_query += """) and b.type = 1
                and b.id > a.id
                group by a.id
                order by a.id) as s
                where bLastIvl < aLastIvl
                limit %s) as o
                where ease > 1""" % lapsed_rev_records
        lapsed_successes = mw.col.db.scalar(lapsed_query)

        lapsed_success_rate = int(100 * lapsed_successes / lapsed_rev_records)
        return lapsed_success_rate

    #Find number of lapsed review records in deck
    def lapsed_records_in_deck(deck_id, from_date):
        lapsed_query = """select count() from
                (select min(b.id) as bid, a.id as aid, a.ivl, a.lastIvl as aLastIvl, b.ivl as bIvl, b.lastIvl as bLastIvl, b.ease
                from revlog as a, revlog as b, cards as c
                where
                a.id > %s
                and a.type = 1
                and a.ease = 1
                and a.cid = b.cid
                and a.cid = c.id
                and c.did = %s
                and b.type = 1
                and b.id > a.id
                group by a.id
                order by a.id) as s
                where bLastIvl < aLastIvl""" % (from_date, deck_id)
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
        if (cur_date - from_date) < (24 * 60 * 60 * 1000):
            #utils.showInfo("Waiting 24 hours to adjust Lapse Next Interval for %s." % name)
            return False, False
        if group_id:
            # Find decks and cycle through
            decks = find_decks_in_settings_group(group_id)
            for d in decks:
                deck_ids.append(d)
                lapsed_rev_records += lapsed_records_in_deck(d, from_date)
            # make sure we have enough records in review to
            if lapsed_rev_records >= min_look_back:
                lapsed_success_rate = deck_lapsed_success_rate(deck_ids, lapsed_rev_records) #look back over all records since last adjustment
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
        dconf = mw.col.decks.dconf
        name = dconf[group_id]['name']
        if name not in previous[profile]:
            previous[profile][name] = {}
        cur_LNIvl = float(mw.col.decks.dconf[group_id]['lapse']['mult'])
        lapsed_success_rate, lapsed_rev_records = og_lapsed_success_rate(name, card_sample_size)
        # Returns False, False if we don't have enough review records since last time.
        if lapsed_success_rate and lapsed_rev_records and lapsed_success_rate != tsr:
            target_rate = float(tsr) / 100
            cur_rate = float(lapsed_success_rate) / 100
            #Simplistic ratio adjustment
            new_LNIvl = round(cur_LNIvl * cur_rate/target_rate, 2)
            if new_LNIvl > 1:
                new_LNIvl = 1
            if utils.askUser("%s"
                    "\n\nLapsed Card Success Rate: %s"
                    "\nTarget Success Rate: %s"
                    "\nCurrent lapsed new interval: %s"
                    "\nSuggested interval: %s"
                    "\n\nAccept new Lapsed new interval?" % (
                    name, cur_rate, target_rate, cur_LNIvl, new_LNIvl)):
                # make changes
                mw.col.decks.dconf[group_id]['lapse']['mult'] = new_LNIvl
                mw.col.decks.save(mw.col.decks.dconf[group_id])
                previous[profile][name]['lapsed'] = intTime(1000)
                #utils.showInfo("Updating lapsed new interval currently disabled")
        else:
            if not silent:
                utils.showInfo("Lapsed New Interval\n\nNot enough records for options group %s" % name)

    def eval_lapsed_newIvl(silent=False):
        #find all deck options groups
        dconf = mw.col.decks.dconf
        for og in dconf:
            adj_lapsed_newIvl(og, silent)
