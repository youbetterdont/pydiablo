# pydiablo
pydiablo is a Diablo 2 toolkit written in Python. The original goal was to calculate and simulate the time required to kill specific monsters using different builds and equipment. The library is still in early stages. It currently has an accurate monster stats parser and the beginnings of a weapon speed calculator.

## usage

### monster stats
```python
import sys
import pydiablo as d2
# interesting monster_ids
# unraveler5: wave2 minions
# unraveler8/9: high exp dudes in WSK/throne
# bloodlord5: death lords in WSK/throne
# fallen5: wave1 minions
# dkfig2, dkmag2: act5 doom knights and oblivion knights
# venomlord: wave4
# baalhighpriest: wave3
# baalminion1: wave5
monster_id = 'doomknight1'
difficulty = d2.HELL
# write the area table (if we want to choose a specific area)
d2.Monster.levels.write_area_table(sys.stdout, monster_id, difficulty)
# with no specific area chosen, it defaults to highest level available
MonsterType = d2.MinionMonster.create_monster_type(monster_id, difficulty)
print('========')
print('Class name: ' + MonsterType.__name__)
print('Areas: ' + str(MonsterType.mlvl_specific_area_names()))
print('Monster: ' + MonsterType.monster_name())
print('mlvl: ' + str(MonsterType.mlvl))
print('hp range: ' + str(MonsterType.base_hp()))
print('exp: ' + str(MonsterType.base_experience()))
print('block chance: ' + str(MonsterType.block_chance()))
print('defense: ' + str(MonsterType.base_defense()))
print('cold effect: ' + str(MonsterType.cold_effect()))
print('drain effect: ' + str(MonsterType.drain_effect()))
print('fire resist: ' + str(MonsterType.base_fire_resist()))
print('cold resist: ' + str(MonsterType.base_cold_resist()))
print('lightning resist: ' + str(MonsterType.base_lightning_resist()))
print('poison resist: ' + str(MonsterType.base_poison_resist()))
print('damage resist: ' + str(MonsterType.base_damage_resist()))
print('magic resist: ' + str(MonsterType.magic_resist()))

monster = MonsterType(player_count=8, rand=False)
print('==========')
print('max_life: ' + str(monster.max_life))
print('experience: ' + str(monster.experience()))
```

### weapon speed
```python
import sys
import pydiablo as d2

# write a few selected ias breakpoint tables
d2.write_bp_table(sys.stdout, d2.Amazon.strafe_duration, 'BOW', 100, 0, 10)
d2.write_bp_table(sys.stdout, d2.WolfDruid.fury_duration, 'STF', 100, 68, 10, WIAS=90)
d2.write_bp_table(sys.stdout, d2.Paladin.zeal_duration, '2HS', 100, 37, 10, WIAS=0)
d2.write_bp_table(sys.stdout, d2.Act2Merc.jab_duration, 'HTH', 100, 0, -10)
```

## license
See the LICENSE file for license details on pydiablo.py. The files in data and data2 are derivative of Diablo 2 game data; the license in the LICENSE file does not apply.
