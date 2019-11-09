from pydiablo.d2data import D2Data
import bisect

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
                if area_id >= 0:
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

class TreasureClassEx(D2Data):
    @staticmethod
    def filling_values():
        fv = {}
        difficulties = ('', 'N', 'H')
        for difficulty in difficulties:
            item_cols = ['Item{}'.format(x) for x in range(1,11)]
            prob_cols = ['Prob{}'.format(x) for x in range(1,11)] + ['NoDrop']
            mod_cols = ['Unique', 'Set', 'Rare', 'Magic']
            for col in item_cols:
                fv[col] = ''
            for col in prob_cols+mod_cols:
                fv[col] = 0
        return fv

    def __init__(self, filename):
        D2Data.__init__(self, filename, 'Treasure_Class')
        self.group_map = {}
        for tc in self.data['Treasure_Class']:
            if tc:
                group = self.get_data(tc, 'group')
                if group > 0:
                    if group not in self.group_map:
                        self.group_map[group] = []
                    self.group_map[group].append({'Treasure_Class': tc, 'level': self.get_data(tc, 'level')})
        # make sure each group list is sorted by level
        for group, tcs in self.group_map.items():
            tcs.sort(key=lambda x: x['level'])

    def get_upgrade(self, base_tc, mlvl):
        """
        Return the upgraded TC given the base treasure class and the monster level.

        This doesn't handle group 18 correctly.
        """
        group = self.get_data(base_tc, 'group')
        base_level = self.get_data(base_tc, 'level')
        if base_level > mlvl:
            return base_tc
        if group > 0:
            tcs = self.group_map[group]
            levels = [tc['level'] for tc in tcs]
            i = bisect.bisect_right(levels, mlvl)
            if i:
                return tcs[i-1]['Treasure_Class']
            raise ValueError
        else:
            return base_tc


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
    tcex = TreasureClassEx('data/global/excel/TreasureClassEx.txt')
    mumod_const = MonUModConstants('data/global/excel/monumod.txt')
    tc_id = 1 # used for TC lookup. 1 = normal, 2 = champ, 3 = unique
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

    @classmethod
    def monster_ids(cls):
        """Yield monster_ids from monstats.txt in the order in which they are listed."""
        monster_ids = cls.monstats.data['Id']
        for monster_id in monster_ids:
            yield monster_id

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
    def treasure_class(cls):
        """
        Return the treasure class of the monster type, accounting for upgrades.

        Quest drops are not handled yet.
        """
        base_tc = cls.monstats.get_data(cls.monster_id, 'TreasureClass{}'.format(cls.tc_id)+cls.difficulty)
        if cls.difficulty != NORMAL:
            return cls.tcex.get_upgrade(base_tc, cls.mlvl)
        else:
            return base_tc

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
    tc_id = 3

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
    tc_id = 2

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
