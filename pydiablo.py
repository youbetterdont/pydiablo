import numpy as np
import warnings
import collections
import urllib
import logging
import json

logger = logging.getLogger('pydiablo')
logger.setLevel(logging.DEBUG)
#fh = logging.FileHandler('pydiablo.log')
fh = logging.StreamHandler()
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


def eias(ias):
    return np.floor(120. * (ias) / (120 + (ias))).astype(int)

# AnimLength: frames per direction in AnimData.txt
# AnimSpeed: AnimData.txt
# AnimRate: Slowing effects
def anim_duration(AnimLength, AnimSpeed, AnimRate, SIAS, WSM, IASItem, WIAS=0, rollback=100):
    EIAS = eias(IASItem+WIAS)
    speed_increase = min(AnimRate + SIAS + EIAS - WSM, 175)
    # numerator AnimSpeed is always 256 for attacks (only numerator?)
    return (np.ceil((np.ceil(AnimLength*rollback/100.) * 256) / np.floor(AnimSpeed * (speed_increase) / 100.)) - 1).astype('int')

def anim_duration_seq(AnimLength, AnimSpeed, AnimRate, SIAS, WSM, IASItem, WIAS=0, rollback=100):
    EIAS = eias(IASItem+WIAS)
    speed_increase = min(AnimRate + SIAS + EIAS - WSM, 175)
    # AnimSpeed is always 256 for attacks (this is also from AnimData.txt)
    return np.ceil((np.ceil(AnimLength*rollback/100.) * 256) / np.floor(AnimSpeed * (speed_increase) / 100.)).astype('int')

def anim_speed(anim_duration, aidelay=0):
    avg_duration = 1.0*(sum(anim_duration)+aidelay)/len(anim_duration)
    return 25.0/avg_duration

def breakpoints(anim_duration_function, wtype, AnimRate, SIAS, WSM, WIAS=0):
    meias = np.array(range(120))
    mias = np.ceil(meias*120./(120-meias)).astype('int')-WIAS
    ias_list = list(mias[mias >= 0])
    #ias_list = range(200)
    total_dur_prev = 0
    bps = []
    for ias in ias_list:
        total_dur = sum(anim_duration_function(wtype, AnimRate, SIAS, WSM, ias, WIAS=WIAS))
        if total_dur != total_dur_prev:
            bps.append(ias)
        total_dur_prev = total_dur
    return bps
   # print np.diff(np.floor(120.*(ias)/(120+(ias))))

# take the raw rowdata from the animdata file for a particular animation and return the position of the action flag
def action_flag_position(animdata):
    framedata = animdata[2:]
    return np.nonzero(framedata)[0][0]

#get_breakpoints(0,0,0,0,0)

def write_bp_table(iostream, anim_duration_function, wtype, AnimRate, SIAS, WSM, WIAS=0):
    iostream.write('Class: ' + anim_duration_function.__self__.__name__ + '\n')
    iostream.write('Animation: ' + anim_duration_function.__name__.split('_')[0] + '\n')
    iostream.write('Weapon: ' + wtype + '\n')
    iostream.write('AnimRate: ' + str(AnimRate) + '\n')
    iostream.write('SIAS: ' + str(SIAS) + '\n')
    iostream.write('WSM: ' + str(WSM) + '\n')
    iostream.write('WIAS: ' + str(WIAS) + '\n')
    metadata = {'anim_name': anim_duration_function.__name__,
                'wtype': wtype,
                'anim_rate': AnimRate,
                'sias': SIAS,
                'wsm': WSM}
    header = ['ias']
    header += ['eias']
    first_run = True
    bps = breakpoints(anim_duration_function, wtype, AnimRate, SIAS, WSM, WIAS=WIAS)
    aidelay = anim_duration_function.__self__.aidelay
    for bp in bps:
        #for anim_duration_function in anim_duration_functions:
        mlist = anim_duration_function(wtype, AnimRate, SIAS, WSM, bp, WIAS=WIAS)
        if first_run:
            header += ['atk{:d}'.format(x) for x,y in enumerate(mlist)]
            if aidelay:
                header += ['aidelay']
            header += ['avg']
        mstr = [str(x) for x in mlist]
        if aidelay:
            mstr.append(str(aidelay))
        mstr.append('{:.2f}'.format(1.0*(sum(mlist)+aidelay)/len(mlist)))
        mstr.append('{:.2f}'.format(anim_speed(mlist, aidelay=aidelay)))
        mstr.insert(0, str(bp))
        mstr.insert(1, str(eias(bp+WIAS)-WSM+SIAS))
        if first_run:
            header += ['aps']
            iostream.write('\t'.join(header) + '\n')
        iostream.write('\t'.join(mstr) + '\n')
        #mstr = '\t'.join([d for d in mline])
        #if mstr != mstr_prev:
        #    return_str += '\t'.join([str(ias), mstr])
        #    return_str += '\n'
        #mstr_prev = mstr
        first_run = False
    #mdtype = ['float64']*len(header)
    #np_tbl = np.rec.array(tbl, dtype=zip(header, mdtype))

#def print_table(tbl, metadata):
#    for row in tbl:
#        print row

class AnimData(object):
    def __init__(self, filename):
        animdata_keys = np.genfromtxt(filename, delimiter='\t', names=True, dtype=None, usecols=0, encoding=None)['CofName']
        animdata = np.genfromtxt(filename, delimiter='\t', skip_header=1, dtype='int', encoding=None)
        self.animdata_dict = dict(zip(animdata_keys, [row[1:] for row in animdata]))

    def get_data(self, key):
        return self.animdata_dict[key]

class Character(object):
    animdata = AnimData('data2/animdata.txt')
    # constants for interpreting json character data
    ITEM_LOCATION_STORED = 0
    ITEM_LOCATION_EQUIPPED = 1
    ITEM_LOCATION_BELT = 2

    ITEM_ALT_POSITION_INVENTORY = 1
    ITEM_ALT_POSITION_CUBE = 4
    ITEM_ALT_POSITION_STASH = 5

    # this is a bit ugly, but we need to know if any item is a charm to determine
    # if we should use the item or not
    CHARM_ITEM_TYPES = ['cm1', 'cm2', 'cm3']

    # see http://www.mannm.org/d2library/faqtoids/animspeed.html#startframes
    startframes = {'HTH': 0,
                   'BOW': 0,
                   '1HS': 0,
                   '1HT': 0,
                   'STF': 0,
                   '2HS': 0,
                   '2HT': 0,
                   'XBW': 0}

    aidelay = 0

    #def __init__(self):
    #    self.weapon = None #HandToHand()
    #    self.equipment = []

    #def equip_weapon(self, weapon):
    #    self.weapon = weapon

    #def equip(self, equipable):
    #    self.equipment.append(equipable)

    def __init__(self, chardata):
        self.chardata = chardata
        self.character = chardata['character']
        self.d2s = self.character['d2s']
        self.header = self.d2s['header']
        self.attributes = self.d2s['attributes']
        self.skills = self.d2s['skills']
        self.items = self.d2s['items']
        self.corpse_items = self.d2s['corpse_items']
        self.merc_items = self.d2s['merc_items']

    def name(self):
        return self.header['name']

    def level(self):
        return self.header['level']

    @classmethod
    def is_equipped(cls, item):
        return item['location_id'] == cls.ITEM_LOCATION_EQUIPPED

    @classmethod
    def in_inventory(cls, item):
        return item['location_id'] == cls.ITEM_LOCATION_STORED and item['alt_position_id'] == cls.ITEM_ALT_POSITION_INVENTORY

    @classmethod
    def is_charm(cls, item):
        return item['type'] in cls.CHARM_ITEM_TYPES

    @classmethod
    def use_item(cls, item):
        return cls.is_equipped(item) or cls.in_inventory(item) and cls.is_charm(item)

    #def deadly_strike(self):
    #    for item in self.items:
    #        if self.use_item(item):


    @classmethod
    def get_char_animdata(cls, AnimName, wtype):
        animkey = cls.ctype + AnimName + wtype
        return cls.animdata.get_data(animkey)

    @classmethod
    def anim_duration(cls, AnimName, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0, rollback=100):
        animdata = cls.get_char_animdata(AnimName, wtype)
        return anim_duration(animdata[0], animdata[1], AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, rollback=rollback)

    # the length of the animation used for serial attacks, like zeal or fury
    @classmethod
    def base_foreswing_frames(cls, animdata, wtype, first=False):
        af = action_flag_position(animdata)
        if first:
            af -= cls.startframes[wtype]
        return af

    @classmethod
    def foreswing_duration(cls, AnimName, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0, first=False, rollback=100):
        animdata = cls.get_char_animdata(AnimName, wtype)
        #print animdata
        af = cls.base_foreswing_frames(animdata, wtype, first)
        return anim_duration_seq(af, animdata[1], AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, rollback=rollback)

    @classmethod
    def avg_attack_duration(cls, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        return sum(cls.attack_duration(wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS))/2.0

    #def avg_attack_duration_as_equipped(self, AnimRate, SIAS, IASItem):
    #    wtype = self.weapon.wtype
    #    wias = self.weapon.mp.ias
    #    wsm = self.weapon.wsm
    #    return self.avg_attack_duration(wtype, AnimRate, SIAS, wsm, IASItem, WIAS=wias)

    #@classmethod
    #def avg_action_frame(cls, wtype, AnimRate, SIAS, WSM, IASItem):
    #    return (cls.action_frame('A1', wtype, AnimRate, SIAS, WSM, IASItem)\
    #            +cls.action_frame('A2', wtype, AnimRate, SIAS, WSM, IASItem))/2.0

    @classmethod
    def attack_duration(cls, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        a1_dur = cls.anim_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)
        try:
            a2_dur = cls.anim_duration('A2', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)
        except KeyError as e:
            return [a1_dur]
        return [a1_dur, a2_dur]

    @classmethod
    def zeal_duration(cls, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        return [cls.foreswing_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, first=True)] +\
                [cls.foreswing_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)]*3 +\
                [cls.anim_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)]

class Paladin(Character):
    ctype = 'PA'

class Druid(Character):
    ctype = 'DZ'

class Barbarian(Character):
    ctype = 'BA'

class Assassin(Character):
    ctype = 'AI'

class Necromancer(Character):
    ctype = 'NE'

class Transform(object):
    @classmethod
    def get_xform_animdata(cls, AnimName):
        key = cls.ttype + AnimName + 'HTH'
        return cls.animdata.get_data(key)

    @classmethod
    def modified_anim_speed(cls, AnimName, wtype, WSM, WIAS):
        frames_neutral = cls.get_xform_animdata('NU')[0]
        if wtype == '2HS': wtype = '1HS' # TODO: double check this
        chardata = cls.get_char_animdata(AnimName, wtype)
        frames_char = chardata[0]
        char_speed = chardata[1]
        delay = np.floor(256.*frames_char / np.floor((100.+WIAS-WSM) * char_speed/100.))
        return int(np.floor(256.*frames_neutral / delay))

    @classmethod
    def anim_duration(cls, AnimName, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        animdata = cls.get_xform_animdata(AnimName)
        animlength = animdata[0]
        animspeed = cls.modified_anim_speed(AnimName, wtype, WSM, WIAS)
        #eias = int(np.floor(120 * (IASItem+WIAS) / (120 + (IASItem+WIAS))))
        #speed_increase = AnimRate + SIAS + eias - WSM
        #if speed_increase > 175:
        #    SIAS = SIAS - (speed_increase-175)
        return anim_duration(animlength, animspeed, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)

    @classmethod
    def foreswing_duration(cls, AnimName, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0, first=False):
        animdata = cls.get_xform_animdata(AnimName)
        #print animdata
        af = cls.base_foreswing_frames(animdata, wtype, first)
        animspeed = cls.modified_anim_speed(AnimName, wtype, WSM, WIAS)
        return anim_duration_seq(af, animspeed, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)

class Werewolf(Transform):
    ttype = '40'

    @classmethod
    def fury_duration(cls, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        return cls.zeal_duration(wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS)

class Werebear(Transform):
    ttype = 'TG'

class WolfDruid(Werewolf, Druid):
    pass

class WolfBarbarian(Werewolf, Barbarian):
    pass

class BearDruid(Werebear, Druid):
    pass

class Sorceress(Character):
    ctype = 'SO'
    startframes = {'HTH': 1,
                   'BOW': 0,
                   '1HS': 2,
                   '1HT': 2,
                   'STF': 2,
                   '2HS': 2,
                   '2HT': 0,
                   'XBW': 0}

class Amazon(Character):
    ctype = 'AM'
    startframes = {'HTH': 1,
                   'BOW': 0,
                   '1HS': 2,
                   '1HT': 2,
                   'STF': 2,
                   '2HS': 2,
                   '2HT': 0,
                   'XBW': 0}

    # strafe is not quite matching the german calc or the amazon basin tables for crossbows (which dont agree themselves).
    # Main problem is that crossbows seem to have unequal length follow up frames. I don't care enough to figure this
    # out for now. Bow breakpoints seem fine.
    # Problems for 0 WSM XBW:
    # * Missing 14 and 68 IAS BPs due to unequal length follow up frames (both German and AB show this)
    # * Differ with AB at 30 IAS for one follow up frame (German does not have this BP)
    # * Differ in length of last attack at 32 IAS BP. German and AB both agree this is 11 frames, but then AB
    #   says the next BP is 12 frames (??). This calc returns 12 frames.
    # * Differ in one follow up frame at 75 IAS BP where German and AB agree
    # * Differ in last attack length at 152 IAS (German does not have this BP)
    @classmethod
    def strafe_duration(cls, wtype, AnimRate, SIAS, WSM, IASItem, WIAS=0):
        if wtype=='XBW':
            warnings.warn("Crossbow strafe not completely accurate. See {} documentation.".format(cls.strafe_duration.__name__))
        return [max(cls.foreswing_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, first=True),5)] +\
                [max(cls.foreswing_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, rollback=50),3)]*8 +\
                [max(cls.anim_duration('A1', wtype, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, rollback=78),7)]
                #[anim_duration(16, 256, AnimRate, SIAS, WSM, IASItem, WIAS=WIAS, rollback=100)]


class Act1Merc(Character):
    ctype = 'RG'

class Act2Merc(Character):
    ctype = 'GU'
    JAB_DURATION = 14 # seems to be the right magic number
    aidelay = 2

    @classmethod
    def attack_duration(cls, wtype, AnimRate, SIAS, WSM, ias, WIAS=0):
        return [cls.anim_duration('A1', 'HTH', AnimRate, SIAS, WSM, ias, WIAS=WIAS)]

    @classmethod
    def jab_duration(cls, wtype, AnimRate, SIAS, WSM, ias, WIAS=0):
        # a2 merc only has HTH animation defined. this function ignores wtype
        return [anim_duration_seq(cls.JAB_DURATION, 256, AnimRate, SIAS, WSM, ias, WIAS=WIAS),0]

class Act3Merc(Character):
    ctype = 'IW'

class Act5Merc(Character):
    ctype = '0A'

# constants related to accessing slash data
SLASH_URL = "https://armory.slashdiablo.net/retrieving/v1/character?name={}"
SLASH_CLASS_MAP = {'Sorceress': Sorceress,
                   'Amazon': Amazon,
                   'Druid': Druid,
                   'Barbarian': Barbarian,
                   'Assassin': Assassin,
                   'Necromancer': Necromancer,
                   'Paladin': Paladin}

def create_from_slash(char_name):
    try:
        contents = urllib.request.urlopen(SLASH_URL.format(char_name)).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("Could not find character {}. Armory down or missing character.".format(char_name)) from e
    chardata = json.loads(contents)
    try:
        charclass = chardata['character']['d2s']['header']['class']
    except KeyError as e:
        logger.error("Problem accessing character data. JSON dump: {}".format(chardata))
        raise RuntimeError("Bad character data. Top level keys: {}".format(chardata.keys())) from e
    logger.debug("{} is a {}".format(char_name, charclass))
    return SLASH_CLASS_MAP[charclass](chardata)



# This should probably be an enum, but it's more convenient this way
NORMAL = ''
NIGHTMARE = 'N'
HELL = 'H'

# TODO: Move these to class level constants
# mlvl bonuses (can't find these in data files)
SUPER_UNIQUE_MONSTER_MLVL_BONUS = 3
UNIQUE_MONSTER_MLVL_BONUS = 3
MINION_MONSTER_MLVL_BONUS = 3
CHAMPION_MONSTER_MLVL_BONUS = 2

SUPER_UNIQUE_MONSTER_EXP_BONUS = 5
UNIQUE_MONSTER_EXP_BONUS = 5
MINION_MONSTER_EXP_BONUS = 5
CHAMPION_MONSTER_EXP_BONUS = 3

# exp and hp bonus percentages with player count
EXP_BOOST_PER_PLAYER = 50
HP_BOOST_PER_PLAYER = 50

# damage bonuses (apply only in nightmare and hell)
DMG_BOOST_PER_PLAYER = 6.25
# TODO: Damage boosts not yet implemented

class D2Data(object):
    @staticmethod
    def filling_values():
        return None

    def __init__(self, filename, key, usecols=None):
        self.data = np.genfromtxt(filename, delimiter='\t', names=True, dtype=None,
                                  filling_values=self.filling_values(), usecols=usecols, encoding=None)
        self.idx = dict(zip(self.data[key], range(len(self.data[key]))))

    def get_data(self, key, col):
        return self.data[col][self.idx[key]]

class Monstats(D2Data):
    @staticmethod
    def filling_values():
        fv = {}
        difficulties = ('', 'N', 'H')
        for difficulty in difficulties:
            cols = ['ResFi', 'ResLi', 'ResCo', 'ResPo', 'ResMa', 'ResDm',
                    'coldeffect', 'Drain', 'A1MinD', 'A1MaxD', 'A2MinD', 'A2MaxD',
                    'S1MinD', 'S1MaxD', 'A1TH', 'A2TH', 'S1TH', 'Exp', 'AC']
            for col in cols:
                fv[col+difficulty] = 0
        return fv

    def __init__(self, filename):
        D2Data.__init__(self, filename, 'Id')

class MonLvl(D2Data):
    def __init__(self, filename):
        D2Data.__init__(self, filename, 'Level')

class MonProp(D2Data):
    def __init__(self, filename):
        D2Data.__init__(self, filename, 'Id')

class SuperUniques(D2Data):
    def __init__(self, filename):
        D2Data.__init__(self, filename, 'Superunique')

class MonUModConstants(D2Data):
    DMAP = {'':'', 'N':' (N)','H':' (H)'}

    def __init__(self, filename):
        D2Data.__init__(self, filename, 'constant_desc', usecols=['constant_desc', 'constants'])

class Levels(D2Data):
    DIFFMAP = {NORMAL: 1, NIGHTMARE: 2, HELL: 3}

    def add_minions(self, monmap, mon, area_id):
        minion1 = self.monstats.get_data(mon, 'minion1')
        minion2 = self.monstats.get_data(mon, 'minion2')
        spawn = self.monstats.get_data(mon, 'spawn')
        for minion in [minion1, minion2, spawn]:
            if minion != '':
                if minion not in monmap:
                    monmap[minion] =  []
                #print mon, minion, area_id
                monmap[minion].append(area_id)

    def make_monmap(self, monmap, cols):
        for col in cols:
            mons = self.data[col]
            if mons.dtype == 'bool': continue # this happens if nothing is set in the column
            for i, mon in enumerate(mons):
                if mon == '': continue
                if mon not in monmap:
                    monmap[mon] = []
                area_id = self.data['Id'][i]
                monmap[mon].append(area_id)
                # now add the minions that can spawn this this monster
                self.add_minions(monmap, mon, area_id)
        # now check super unique locations. some monsters only spawn
        # as super uniques or minions of super uniques
        mons = self.superuniques.data['Class']
        for i, mon in enumerate(mons):
            if mon == '': continue
            if mon not in monmap:
                monmap[mon] = []
            suid = self.superuniques.data['Superunique'][i]
            area_id = self.superuniques2.get_data(suid, 'AreaId')
            # TODO: Consider not adding superunique base types. There's
            # really no reason they need to be looked up unless we're
            # spawning a super unique.
            if area_id >= 0:
                #print mon, area_id
                monmap[mon].append(area_id)
            # now check for minions
            # TODO: Consider adding special tag to minions to indicate
            # they only spawn as superunique minions
            self.add_minions(monmap, mon, area_id)
        for key, value in monmap.items():
            monmap[key] = sorted(list(set(monmap[key])))

    def __init__(self, filename, monstats, superuniques, superuniques2):
        D2Data.__init__(self, filename, 'Id')
        # build monster_id -> [level_id] map
        norm_cols = ['mon'+str(i) for i in range(1,11)]
        nmh_cols = ['n'+s for s in norm_cols]
        self.monstats = monstats
        self.superuniques = superuniques
        self.superuniques2 = superuniques2
        self.norm_monmap = {}
        self.nmh_monmap = {}
        self.make_monmap(self.norm_monmap, norm_cols)
        self.make_monmap(self.nmh_monmap, nmh_cols)

    def get_monmap(self, difficulty):
        if difficulty==NORMAL:
            return self.norm_monmap
        else:
            return self.nmh_monmap

    def get_areas(self, monster_id, difficulty):
        try:
            area_ids = self.get_monmap(difficulty)[monster_id]
        except KeyError as e:
            area_ids = []
        area_names = self.area_names(area_ids)
        return zip(area_ids, [self.area_level(area_id, difficulty) for area_id in area_ids], area_names)

    def write_area_table(self, iostream, monster_id, difficulty):
        iostream.write('Id\tAlvl\tLevelName\n')
        areas = self.get_areas(monster_id, difficulty)
        for area in areas:
            iostream.write('{:d}\t{:d}\t{:s}\n'.format(*area))

    def area_names(self, area_ids):
        return [self.area_name(area_id) for area_id in area_ids]

    def area_name(self, area_id):
        return self.get_data(area_id, 'LevelName')

    def area_level(self, area_id, difficulty):
        return self.get_data(area_id, 'MonLvl'+str(self.DIFFMAP[difficulty])+'Ex')

class Monster(object):
    mlvl_bonus = 0
    exp_bonus = 1
    monstats = Monstats('data/global/excel/monstats.txt')
    monstats2 = Monstats('data/global/excel/monstats2.txt')
    monlvl = MonLvl('data/global/excel/MonLvl.txt')
    monprop = MonProp('data/global/excel/MonProp.txt')
    superuniques = SuperUniques('data/global/excel/SuperUniques.txt')
    superuniques2 = SuperUniques('data2/SuperUniques2.txt')
    levels = Levels('data/global/excel/Levels.txt', monstats, superuniques, superuniques2)
    mumod_const = MonUModConstants('data/global/excel/monumod.txt')
    # map monstats stats to monlvl stats, assuming ladder or single player
    STATMAP = {'maxHP' : 'LHP', 'minHP': 'LHP', # capitalization typo (?) for normal difficulty
               'MaxHP' : 'LHP', 'MinHP': 'LHP',
               'AC': 'LAC',
               'Exp': 'LXP',
               'A1MinD': 'LDM', 'A1MaxD': 'LDM',
               'A2MinD': 'LDM', 'A2MaxD': 'LDM',
               'S1MinD': 'LDM', 'S1MaxD': 'LDM',
               'A1TH': 'LTH', 'A2TH': 'LTH', 'S1TH': 'LTH'}

    def __init__(self, player_count=1, rand=False):
        self.player_count = player_count
        self.max_life = self._max_life(rand)
        self.current_life = self.max_life

    def _max_life(self, rand=False):
        if rand:
            life = np.random.randint(*self.base_hp())
        else:
            life = sum(self.base_hp())//2
        return life*(100+(self.player_count-1)*HP_BOOST_PER_PLAYER)//100

    def experience(self):
        return self.base_experience()*(100+(self.player_count-1)*EXP_BOOST_PER_PLAYER)//100

    #def apply_curse(self, curse):
        #self.curse.disable()
        #setattr(self, curse.effect, curse.val)

    #def damage_resist(self):
    #    return self.base_damage_resist() + self.curse.damage_resist()

    # create and return a type given the monster id, difficulty, and area id. If no area id is given,
    # use the area id that will result in the highest mlvl.
    @classmethod
    def create_monster_type(cls, monster_id, difficulty, area_id=None):
        MonsterType = type(monster_id+difficulty+str(area_id)+cls.__name__, (cls,),
                           {'monster_id': monster_id, 'difficulty': difficulty})
        # try to get an mlvl first, even if area_id is None
        try:
            MonsterType.mlvl = MonsterType.mlvl_from_area(area_id)
        except KeyError as e:
        # if that failed, then attempt to use an area id with the highest possible mlvl
        #if MonsterType.area_id is None:
            area_ids = MonsterType.area_ids()
            if len(area_ids) > 0:
                mlvls = [MonsterType.levels.area_level(x, MonsterType.difficulty) for x in area_ids]
                #f = lambda x: mlvls[x]
                #MonsterType.area_id = area_ids[max(range(len(mlvls)), key=f)]
                MonsterType.mlvl = max(mlvls)
            else:
                raise RuntimeError('Unable to find an mlvl for {}.'.format(monster_id))
        MonsterType.mlvl += cls.mlvl_bonus
        return type(monster_id+difficulty+str(MonsterType.mlvl)+cls.__name__, (cls,),
                           {'monster_id': monster_id, 'difficulty': difficulty, 'mlvl': MonsterType.mlvl})
    @classmethod
    def is_boss(cls):
        return cls.monstats.get_data(cls.monster_id, 'boss') == 1

    @classmethod
    def mlvl_specific_area_ids(cls):
        try:
            area_ids = cls.area_ids()
        except KeyError as e:
            return []
        mlvls = [cls.levels.area_level(x, cls.difficulty) for x in area_ids]
        ret = []
        for area_id, mlvl in zip(area_ids, mlvls):
                if mlvl == cls.mlvl-cls.mlvl_bonus or cls.is_boss(): ret.append(area_id)
        return ret

    @classmethod
    def area_ids(cls):
        return cls.levels.get_monmap(cls.difficulty)[cls.monster_id]

    @classmethod
    def area_names(cls):
        return cls.levels.area_names(cls.area_ids())

    @classmethod
    def mlvl_specific_area_names(cls):
        return [cls.levels.area_name(area_id) for area_id in cls.mlvl_specific_area_ids()]

    @classmethod
    def monster_name(cls):
        return cls.monstats.get_data(cls.monster_id, 'NameStr')

    @classmethod
    def mlvl_from_area(cls, area_id):
        if cls.is_boss() or cls.difficulty==NORMAL:
            return cls.monstats.get_data(cls.monster_id, 'Level'+cls.difficulty)
        else:
            #if area_id is None:
            #    raise RuntimeError('Must specify area_id for non-boss monsters!')
            #lvl_ids = cls.levels.get_monmap(difficulty)[monster_id]
            return cls.levels.area_level(area_id, cls.difficulty)

    @classmethod
    def ratioed_stat(cls, stat):
        ratio = cls.monstats.get_data(cls.monster_id, stat+cls.difficulty)
        # if noratio is set (never?), then it's not a ratio, it's the actual stat
        if cls.monstats.get_data(cls.monster_id, 'noRatio')==1:
            return ratio
        else:
            #mlvl = cls.mlvl()
            base = cls.monlvl.get_data(cls.mlvl, cls.STATMAP[stat]+cls.difficulty)
            return base*ratio//100

    @classmethod
    def base_hp(cls):
        stat_strs = ('minHP', 'maxHP') if cls.difficulty==NORMAL else ('MinHP', 'MaxHP')
        return tuple(map(lambda s: cls.ratioed_stat(s)*(100+cls.hp_bonus())//100, stat_strs))

    @classmethod
    def hp_bonus(cls):
        return 1

    @classmethod
    def block_chance(cls):
        try:
            block_anim_enabled = cls.monstats2.get_data(cls.monster_id, 'mBL')==1
        except KeyError as e:
            return 0
        block_without_shield = cls.monstats.get_data(cls.monster_id, 'NoShldBlock')==1
        if block_anim_enabled or block_without_shield:
            return max(cls.monstats.get_data(cls.monster_id, 'ToBlock'+cls.difficulty),0)
        else:
            return 0

    @classmethod
    def base_experience(cls):
        return cls.ratioed_stat('Exp')*cls.exp_bonus

MONSTER_M_NAMES = {'base_fire_resist': 'ResFi',
                   'base_cold_resist': 'ResCo',
                   'base_lightning_resist': 'ResLi',
                   'base_poison_resist': 'ResPo',
                   'base_damage_resist': 'ResDm',
                   'magic_resist': 'ResMa',
                   'cold_effect': 'coldeffect',
                   'drain_effect': 'Drain'}

# adding classmethods this way won't work if you move the setattr call directly into the for loop.
# something about for loop variable scoping
def add_stat_accessor(key, val):
    setattr(Monster, key, classmethod(lambda cls: cls.monstats.get_data(cls.monster_id, val+cls.difficulty)))

for key, val in MONSTER_M_NAMES.items():
    add_stat_accessor(key, val)

MONSTER_RANGE_NAMES = {'base_a1_damage': ('A1MinD', 'A1MaxD'),
                       'base_a2_damage': ('A2MinD', 'A2MaxD'),
                       'base_s1_damage': ('S1MinD', 'S1MaxD')}

def add_range_stat_accessor(key, val):
    setattr(Monster, key,
            classmethod(lambda cls: tuple(map(lambda s: cls.ratioed_stat(s), val))))

for key, val in MONSTER_RANGE_NAMES.items():
    add_range_stat_accessor(key, val)

MONSTER_RATIO_NAMES = {'base_a1_to_hit': 'A1TH',
                       'base_a2_to_hit': 'A2TH',
                       'base_s1_to_hit': 'S1TH',
                       'base_defense': 'AC'}

def add_ratioed_stat_accessor(key, val):
    setattr(Monster, key, classmethod(lambda cls: cls.ratioed_stat(val)))

for key, val in MONSTER_RATIO_NAMES.items():
    add_ratioed_stat_accessor(key, val)

class UniqueMonster(Monster):
    mlvl_bonus = UNIQUE_MONSTER_MLVL_BONUS
    exp_bonus = UNIQUE_MONSTER_EXP_BONUS

    @classmethod
    def hp_bonus(cls):
        return cls.mumod_const.get_data('unique +hp%'+cls.mumod_const.DMAP[cls.difficulty], 'constants')

class MinionMonster(Monster):
    mlvl_bonus = MINION_MONSTER_MLVL_BONUS
    exp_bonus = MINION_MONSTER_EXP_BONUS

    @classmethod
    def hp_bonus(cls):
        return cls.mumod_const.get_data('minion +hp%'+cls.mumod_const.DMAP[cls.difficulty], 'constants')

class ChampionMonster(Monster):
    mlvl_bonus = CHAMPION_MONSTER_MLVL_BONUS
    exp_bonus = CHAMPION_MONSTER_EXP_BONUS

    @classmethod
    def hp_bonus(cls):
        return cls.mumod_const.get_data('champion +hp%'+cls.mumod_const.DMAP[cls.difficulty], 'constants')

class SuperUnique(UniqueMonster):
    mlvl_bonus = SUPER_UNIQUE_MONSTER_MLVL_BONUS
    exp_bonus = SUPER_UNIQUE_MONSTER_EXP_BONUS

    @classmethod
    def create_superunique_type(cls, superunique, difficulty):
        monster_id = cls.superuniques.get_data(superunique, 'Class')
        rtype = cls.create_monster_type(monster_id, difficulty)
        setattr(rtype, 'superunique', superunique)
        setattr(rtype, '__name__', superunique.replace(' ','')+difficulty+str(rtype.mlvl))
        return rtype

    @classmethod
    def monster_name(cls):
        return cls.superuniques.get_data(cls.superunique, 'Name')
