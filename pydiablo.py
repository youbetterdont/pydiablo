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

class PydiabloError(Exception):
    pass

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

class Stat:
    """This class is a collection of static functions for now.

    """
    #itemstatcost = D2Data('data/global/excel/ItemStatCost.txt', 'Stat')
    itemstatcostid = D2Data('data/global/excel/ItemStatCost.txt', 'ID', usecols=[0,1]);
    properties = D2Data('data/global/excel/Properties.txt', 'code', usecols=range(30))

    @classmethod
    def attribute_to_stats(cls, attr):
        # first handle some special cases where the d2s parser
        # combined some stats into ranges.
        if attr['id'] in [17, 48, 50, 52, 54, 57]:
            stats = []
            for i, value in enumerate(attr['values']):
                stat = cls.itemstatcostid.get_data(attr['id']+i, 'Stat')
                stats.append({'stat': stat, 'values': [value]})
            return stats

        # next deal with the properties giving charges.
        if attr['id'] in range(204,214):
            # override the stat reference to point to a new dict that we will
            # modify so that charges fits in better to our scheme. We recombine
            # the current and maximum charges into one number.
            new_attr = {}
            new_attr['id'] = attr['id']
            try:
                # MSB is maximum charges, LSB is current charges
                new_attr['values'] = [attr['values'][0], attr['values'][1],
                                      attr['values'][2] + 2**8*attr['values'][3]]
            except IndexError as e:
                logger.error("Unexpected values field in item charges attribute. JSON dump: {}".format(attr))
                raise
            attr = new_attr

        # next handle the general case.
        stat = cls.itemstatcostid.get_data(attr['id'], 'Stat')
        return [{'stat': stat, 'values': attr['values']}]

    @classmethod
    def add_attributes_to_map(cls, attr_iterator, stat_map):
        """Add attributes from the item to the stat map.

        Positional arguments:
        attr_iterator -- an iterator for the item attributes.
        stat_map -- add stats to this map

        First, some terminology. Nokka's d2s parser gives 'attributes' for the items.
        These 'attributes' are a little different than the 'stats' in ItemStatCost.txt.
        When referring to the stat as it exists in the JSON from the d2s parser, I will
        use the term 'attribute'. When referring to a stat consistent with ItemStatCost.txt,
        I will use the term 'stat'.

        attr_iterator must yield a map with an id and values field and can
        be created with the generator methods in the Item class. These maps are
        expected to follow the format of nokka's d2s parser. When converting from
        attribute to stat, we change a few things, notably with combined stat ranges
        (min-max dmg) and with charges.

        The stat_map will contain all item stats, keyed by stat id (ItemStatCost.txt).
        In the case of a simple stat (one value), the value for the stat id
        will be a list of all instance values of that stat. In the case of a complex
        stat, the value for the stat id will be another map, keyed by parameter.

        simple attribute:
        > stat_map[141] # deadly strike
        [20]

        complex attribute:
        > stat_map[204][62][30] # level 30 (30) hydra (62) charges (204 is the stat id)
        [2570]
        The game stores the current and max charges as one 16 bit value. In this case,
        there are 10 current charges (LSB) and 10 max (MSB): 2570 = 0x0A0A.
        """
        for attr in attr_iterator:
            for stat in cls.attribute_to_stats(attr):
                mdict = stat_map
                mkey = stat['stat']
                for value in attr['values'][:-1][::-1]:
                    if mkey not in mdict:
                        mdict[mkey] = {}
                    mdict = mdict[mkey]
                    mkey = value
                if mkey not in mdict:
                    mdict[mkey] = []
                mdict[mkey].append(attr['values'][-1])

    @staticmethod
    def create_stat(func, stat, set_, val, param, min_, max_, rand=False):
        """Return a newly created stat as a dict with 'stat_id' and 'values' fields.

        The values are ordered consistenly with the item stat order in the d2s file.
        """
        if rand:
            logger.error("Random generation of stats not yet supported.")
        # The funciton mapping below was reverse engineered from vanilla game data
        # and by comparing to the item stat order in the d2s file (easy to see in nokka's parser).
        # It may not be completely accurate. Surely there are some differences between
        # the otherwise identical functions.
        # TODO: func3 is same as 1, but it should reuse the func1 rolls.
        if func in [1, 3, 8]:
            #stat_id = cls.itemstatcost.get_data(stat, 'ID')
            return {'stat': stat, 'values': [(min_+max_)//2]}
        if func==21:
            #stat_id = cls.itemstatcost.get_data(stat, 'ID')
            return {'stat': stat, 'values': [val, (min_+max_)//2]}
        else:
            return {}

    @classmethod
    def property_functions(cls, prop):
        """Yield a map containing 'set', 'val', 'func', and 'stat' fields for each stat associated with the property."""
        for i in range(1,8): # 7 maximum stats per property
            stat = cls.properties.get_data(prop, 'stat{}'.format(i))
            #stat_id = cls.itemstatcost.get_data(stat, 'ID')
            set_ = cls.properties.get_data(prop, 'set{}'.format(i))
            val = cls.properties.get_data(prop, 'val{}'.format(i))
            func = cls.properties.get_data(prop, 'func{}'.format(i))
            if func.dtype == 'bool' or func == -1:
                return # no additional stats to yield
            yield {'stat': stat, 'set_': set_, 'val': val, 'func': func}

class Item(object):

    # constants for interpreting json character data
    ITEM_LOCATION_STORED = 0
    ITEM_LOCATION_EQUIPPED = 1
    ITEM_LOCATION_BELT = 2

    ITEM_ALT_POSITION_INVENTORY = 1
    ITEM_ALT_POSITION_CUBE = 4
    ITEM_ALT_POSITION_STASH = 5

    ITEM_EQUIPPED_ID_RIGHT_HAND = 4
    ITEM_EQUIPPED_ID_LEFT_HAND = 5

    ITEM_TYPE_ID_WEAPON = 3

    ITEM_QUALITY_SET = 5

    # this is a bit ugly, but we need to know if any item is a charm to determine
    # if we should use the item or not
    CHARM_ITEM_TYPES = ['cm1', 'cm2', 'cm3']


    def __init__(self, itemdata):
        self.item = itemdata

    @classmethod
    def create_item(cls, itemdata):
        if 'quality' in itemdata and itemdata['quality'] is not None:
            if itemdata['quality'] == cls.ITEM_QUALITY_SET:
                return SetItem(itemdata)
        return cls(itemdata)

    def is_equipped(self):
        """Returns true if the given item is equipped."""
        return self.item['location_id'] == self.ITEM_LOCATION_EQUIPPED

    def is_weapon(self):
        return self.item['type_id'] == self.ITEM_TYPE_ID_WEAPON

    def is_right_hand_weapon(self):
        """Returns true if the item is a weapon and is equipped in the right hand (above glove slot)."""
        return self.is_equipped() and self.item['equipped_id'] == self.ITEM_EQUIPPED_ID_RIGHT_HAND and self.is_weapon()

    def is_left_hand_weapon(self):
        """Returns true if the item is a weapon and is equipped in the left hand (above boots)."""
        return self.is_equipped() and self.item['equipped_id'] == self.ITEM_EQUIPPED_ID_LEFT_HAND and self.is_weapon()

    #@classmethod
    #def is_primary_weapon(cls, item):
    #    """Returns true if this item is the primary weapon."""
    #    return

    def in_inventory(self):
        """Returns true if the given item is in the player's inventory."""
        return self.item['location_id'] == self.ITEM_LOCATION_STORED and self.item['alt_position_id'] == self.ITEM_ALT_POSITION_INVENTORY

    def is_charm(self):
        """Returns true if the given item is a charm."""
        return self.item['type'] in self.CHARM_ITEM_TYPES

    def use_item(self):
        """Returns true if the item is used by the player, i.e., equipped or a charm."""
        return self.is_equipped() or self.in_inventory() and self.is_charm()

    def get_socketed_items(self):
        if 'socketed_items' in self.item and self.item['socketed_items'] is not None:
            return [Item(itemdata) for itemdata in self.item['socketed_items']]
        return []

    def attributes(self, attr_name):
        """Return an iterator for attributes associated with attr_name."""
        if attr_name in self.item and self.item[attr_name] is not None:
            for attr in self.item[attr_name]:
                yield attr

    def non_set_attributes(self):
        """Return an iterator for all non-set item attributes."""
        for attribute in self.attributes('magic_attributes'):
            yield attribute
        for attribute in self.attributes('runeword_attributes'):
            yield attribute
        for socketed_item in self.get_socketed_items():
            for attribute in socketed_item.attributes('magic_attributes'):
                yield attribute

    def sets_key(self):
        """Return the key for lookups in the Sets.txt file.

        Returns None unless it's a set item."""
        return None

    def set_attributes(self, num_items):
        """Return an empty iterator. Set items will override this method."""
        return
        yield

class Set():
    sets = D2Data('data/global/excel/Sets.txt', 'index')

    def __init__(self, set_id):
        self.set_id = set_id
        logger.debug("{} is a {} piece set.".format(self.set_name(), self.num_items()))

    def num_items(self):
        return np.sum(SetItem.setitems.data['set'] == self.set_id)

    def sets_data(self, col):
        """Get data from a column of Sets.txt."""
        return self.sets.get_data(self.set_id, col)

    def set_name(self):
        """Return the name of the set."""
        return self.sets.get_data(self.set_id, 'name')

    def _attributes(self, prefix, suffix, start, stop):
        # partial set bonuses first
        for i in range(start, stop):
            for c in suffix:
                propstr = '{}Code{}{}'.format(prefix,i,c)
                parstr = '{}Param{}{}'.format(prefix,i,c)
                minstr = '{}Min{}{}'.format(prefix,i,c)
                maxstr = '{}Max{}{}'.format(prefix,i,c)
                prop = self.sets_data(propstr)
                par = self.sets_data(parstr)
                min_ = self.sets_data(minstr)
                max_ = self.sets_data(maxstr)
                # bool check is because an empty column has bool datatype
                # TODO: Figure out a better way to deal with this before it's all over the place
                if prop.dtype != 'bool' and prop != '':
                    logger.debug("Found property {} to include from {} set.".format(prop, self.set_name())
                            + " This property calls funcions {}.".format(list(Stat.property_functions(prop)))
                               + " Arguments to property function: param={} min={} max={}".format(par, min_, max_))
                    for property_function in Stat.property_functions(prop):
                        stat = Stat.create_stat(**property_function, param=par, min_=min_, max_=max_)
                        logger.debug("Created stat {}.".format(stat))

    def attributes(self, num_items):
        self._attributes('P', ['a','b'], 2, num_items+1)
        if num_items == self.num_items():
            self._attributes('F', [''], 1, 9)

class SetItem(Item):
    # map the set_id from d2s parser to the index used by SetItems.txt
    setitems2 = D2Data('data2/SetItems2.txt', 'set_id')
    setitems = D2Data('data/global/excel/SetItems.txt', 'index')

    def __init__(self, itemdata):
        Item.__init__(self, itemdata)
        try:
            self.set_index = self.setitems2.get_data(itemdata['set_id'], 'index')
            #self.set = Set(self.sets_key())
            logger.debug("Creating {} set item {}.".format(self.sets_key(), self.set_index))
        except KeyError as e:
            logger.error("Set item by quality has no set_id. JSON dump: {}".format(itemdata))
            raise

    def setitems_key(self):
        """Return the key for lookups in the SetItems.txt file."""
        return self.set_index

    def sets_key(self):
        """Return the key for lookups in the Sets.txt file."""
        return self.setitems.get_data(self.set_index, 'set')

    def setitems_data(self, col):
        """Get data from a column of SetItems.txt."""
        return self.setitems.get_data(self.set_index, col)

    def all_set_attributes(self):
        """Return an iterator for lists of set item attributes, active or not.

        Set items have attributes organized as a list of lists. The inner lists
        contain the actual attributes. The outer list is for groups of attributes.
        These attributes are grouped because of the way set bonuses are applied.
        The first group is applied with x many items, second group with y many, etc."""
        for attr_list in self.attributes('set_attributes'):
            yield attr_list

    def set_attributes(self, num_items):
        """Return an iterator for active set attributes."""
        # first figure out if bonuses on this item depend on total items equipped or specific items equipped
        # (Civerb's shield is the only one in the latter category)
        if self.setitems_data('add_func') == 1:
            # add the stats based on which other specific items are present
            logger.error("Sets items with bonuses dependent on specific set items (e.g. Civerb's shield) are not"
                         " yet supported. Bonuses will not be applied on {}".format(self.setitems_key()))
        elif self.setitems_data('add_func') == 2:
            # add the stats based on total number of unique items present
            # first grab the set attributes iterator for the item. This is intentionally
            # only initialized once, and not again in the inner loop. It should advance each
            # time we match the exepcted stats from ItemStatCost with the attributes in the list.
            set_attr_iter = self.all_set_attributes()
            try:
                for i in range(1, num_items):
                    stat_ids = []
                    for c in ['a','b']:
                        propstr = 'aprop{}{}'.format(i,c)
                        #parstr = 'apar{}{}'.format(i,c)
                        #minstr = 'amin{}{}'.format(i,c)
                        #maxstr = 'amax{}{}'.format(i,c)
                        prop = self.setitems_data(propstr)
                        #par = item.setitems_data(parstr)
                        #min_ = item.setitems_data(minstr)
                        #max_ = item.setitems_data(maxstr)
                        # bool check is because an empty column has bool datatype
                        # TODO: Figure out a better way to deal with this before it's all over the place
                        if prop.dtype != 'bool' and prop != '':
                            logger.debug("Found property {} to include on {}.".format(prop, self.setitems_key())
                                + " This property adds stats {}.".format([x['stat'] for x in list(Stat.property_functions(prop))]))
                            stat_ids += list(Stat.property_functions(prop))
                    # we need to find the attribute(s) in the d2s parser that matches the stat ids we look
                    # up from the property to add. We could attempt to look up the stat values themselves
                    # in the txt files, but this isn't the right way to do it. Some stat bonuses on items
                    # are actually variable (see Civerb's shield), so we should respect the values in the
                    # d2s file.
                    if len(stat_ids) > 0:
                        # above condition means there is a bonus we should apply, now we need to match it
                        # to the d2s attributes
                        for attr_list in set_attr_iter:
                            tmp_map = {}
                            Stat.add_attributes_to_map(iter(attr_list), tmp_map)
                            if set(tmp_map.keys()) == set([x['stat'] for x in stat_ids]):
                                logger.debug("Attributes {} active on {}.".format(attr_list, self.setitems_key()))
                                for attr in attr_list:
                                    yield attr
                                break
                            else:
                                raise PydiabloError("Attributes {} did not match expected stat ids {} on {}.".format(attr_list,
                                    stat_ids, self.setitems_key()))
            except PydiabloError as e:
                logger.error("Problem matching the set bonuses from d2s to those expected"
                             " by SetItems.txt ({}). Don't trust set bonuses on this item.".format(str(e)))
                return
        # if the value is 0 (empty), do nothing.

class Character(object):
    animdata = AnimData('data2/animdata.txt')
    #item_stat_cost = D2Data('data/global/excel/ItemStatCost.txt', 'Stat')

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
        self.items = [Item.create_item(itemdata) for itemdata in self.d2s['items']]
        self.corpse_items = self.d2s['corpse_items']
        self.merc_items = self.d2s['merc_items']
        self.build_set_map()
        self.build_stat_maps()

    def name(self):
        return self.header['name']

    def level(self):
        return self.header['level']

    def get_active_items(self):
        """Return a list of the active items, i.e., those that are equipped or charms."""
        active_items = []
        for item in self.items:
            if item.use_item():
                active_items.append(item)
        return active_items

    def get_primary_weapon(self):
        """Return the primary weapon."""
        left_hand_weapon = None
        for item in self.get_active_items():
            if item.is_right_hand_weapon():
                # if the item is in the right hand, then we don't need to look anymore,
                # it is the primary weapon
                return item
            elif item.is_left_hand_weapon():
                left_hand_weapon = item
        # if there was no right hand weapon found, then we return the left hand weapon,
        # which will be None if there was no left hand weapon
        return left_hand_weapon

    def get_secondary_weapon(self):
        """Return the secondary weapon."""
        right_hand_weapon = None
        left_hand_weapon = None
        for item in self.get_active_items():
            if item.is_right_hand_weapon():
                right_hand_weapon = item
            elif item.is_left_hand_weapon():
                left_hand_weapon = item
            if right_hand_weapon is not None and left_hand_weapon is not None:
                # as soon as we find two weapons, we can return the one in the left hand
                return left_hand_weapon
        # get here if we did not find two weapons, in which case there is no secondary
        return None

    def get_active_non_weapons(self):
        """Return a list of non-weapon active items."""
        items = []
        for item in self.get_active_items():
            if not item.is_right_hand_weapon() and not item.is_left_hand_weapon():
                items.append(item)
        return items

    def num_set_items(self, item):
        """Return total number of active set items for the set item 'item'."""
        if item.sets_key() is None: return 0
        n = len(set([item_.setitems_key() for item_ in self.set_map[item.sets_key()]]))
        logger.debug("Processing {} on {} with bonuses from {} items from the {} set.".format(item.setitems_key(), self.name(), n, item.sets_key()))
        return n

    def build_stat_maps(self):
        """Construct the stat maps that will be used to perform O(1) lookup per stat."""
        self.primary_weapon_stats = {}
        self.secondary_weapon_stats = {}
        self.off_weapon_stats = {}
        for item in [self.get_primary_weapon()]:
            if item is not None:
                Stat.add_attributes_to_map(item.non_set_attributes(), self.primary_weapon_stats)
                Stat.add_attributes_to_map(item.set_attributes(self.num_set_items(item)), self.primary_weapon_stats)
        for item in [self.get_secondary_weapon()]:
            if item is not None:
                Stat.add_attributes_to_map(item.non_set_attributes(), self.secondary_weapon_stats)
                Stat.add_attributes_to_map(item.set_attributes(self.num_set_items(item)), self.secondary_weapon_stats)
        for item in self.get_active_non_weapons():
            if item is not None:
                Stat.add_attributes_to_map(item.non_set_attributes(), self.off_weapon_stats)
                Stat.add_attributes_to_map(item.set_attributes(self.num_set_items(item)), self.off_weapon_stats)

    def build_set_map(self):
        """Build a map of the character's set items, keyed by index from Sets.txt.

        Each element of the dict is a list of set items.
        """
        self.set_map = {}
        for item in self.get_active_items():
            if item.sets_key() is not None:
                if item.sets_key() not in self.set_map:
                    self.set_map[item.sets_key()] = []
                self.set_map[item.sets_key()].append(item)


    # TODO: Best way to do this is probably to build a map of stat ids (itemstatcost.txt) to a list of values.
    # We can do this once in the constructor, then we don't have to search through all the items every time.
    #def deadly_strike(self):
    #    """Return character's total effective deadly strike as a percentage."""
    #    deadly_strike = 0
    #    for item in self.get_active_items():
    #        if 'magic_attributes' not in item: continue
    #        for stat in item['magic_attributes']:
    #            if stat['id'] == 141:
    #                deadly_strike += stat['values'][0]
    #            elif stat['id'] == 250:
    #                deadly_strike += stat['values'][0]*self.level()//8
    #    return deadly_strike


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

def chardata_from_slash(char_name):
    try:
        contents = urllib.request.urlopen(SLASH_URL.format(char_name)).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("Could not find character {}. Armory down or missing character.".format(char_name)) from e
    return json.loads(contents)

def create_from_json(chardata):
    try:
        charclass = chardata['character']['d2s']['header']['class']
        char_name = chardata['character']['d2s']['header']['name']
    except KeyError as e:
        logger.error("Problem accessing character data. JSON dump: {}".format(chardata))
        raise RuntimeError("Bad character data. Top level keys: {}".format(chardata.keys())) from e
    logger.debug("{} is a {}".format(char_name, charclass))
    return SLASH_CLASS_MAP[charclass](chardata)


def create_from_slash(char_name):
    chardata = chardata_from_slash(char_name)
    return create_from_json(chardata)


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
