import PySimpleGUI as sg
import json
import pathlib
import pandas as pd
import re
import io
import plotly.express as px
import plotly.graph_objects as go
import numpy as np # this won't actually be needed for launch

track_size = (380, 580)
font_sizes = [14, 12, 10, 15]
sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=150)

'''
Useful demo for swapping entirely different window layouts (it's actually really simple): 
https://pysimplegui.trinket.io/demo-programs#/layouts/swapping-window-layouts

LOG HEADERS:
--Randomized Evolutions--
--Pokemon Base Stats & Types--
--Removing Impossible Evolutions--
--Removing Timed-Based Evolutions--
--Random Starters--
--Move Data--
--Pokemon Movesets--
--TM Moves--
--TM Compatibility--
--Trainers Pokemon--
--Static Pokemon--
--Wild Pokemon--
--In-Game Trades--
--Pickup Items--

might want to consider making a /util/log folder for log layouts and stuff but i'll cross that bridge if/when i get there
'''

log = open('kaizo260.log', encoding="utf8").read()
log.count('\n--')

lsplit = log.split('\n--')

if (lsplit[-1].count('Pokemon X') >= 1):
    game = 'XY'
elif (lsplit[-1].count('Pokemon Y') >= 1):
    game = 'XY'
elif (lsplit[-1].count('Pokemon Omega') >= 1):
    game = 'ORAS'
elif (lsplit[-1].count('Pokemon Alpha') >= 1):
    game = 'ORAS'
elif (lsplit[-1].count('Pokemon Sun') >= 1):
    game = 'SM'
elif (lsplit[-1].count('Pokemon Moon') >= 1):
    game = 'SM'
elif (lsplit[-1].count('Pokemon Ultra') >= 1):
    game = 'USUM'
else:
    game = 'UNK'

if game != 'UNK':
    print(f'Log from pokemon {game}.')
else:
    print('Error reading log.')

if game in ('XY', 'ORAS'):
    gen = 6
    evos = lsplit[1] # done
    mons = lsplit[2] # done
    moves = lsplit[7] # done
    tms = lsplit[8] # done
    tmcompat = lsplit[9] # done
    trainer = lsplit[10] # done
    wildmons = lsplit[12] # done
elif game in ('SM', 'USUM'): # not verified yet, will do after gen 6 is done
    gen = 7
    evos = lsplit[1] 
    mons = lsplit[2] 
    moves = lsplit[7] 
    tms = lsplit[8] 
    tmcompat = lsplit[9] 
    trainer = lsplit[10] 
    wildmons = lsplit[12] 
    tutormoves = lsplit[12]
    tutorcompat = lsplit[12]


def parser(data, pattern, s):
    groups = [m.groupdict() for line in data.split(sep=s) if (m := re.match(pattern, line))]
    return groups

# evolutions
# evos_regex = r'(?P<preevo>\S+)+\s+(?P<postevo>\S+)?'
# evos_df = pd.DataFrame(parser(evos.replace('->', ''), evos_regex, '\n')[1:])
evos_df = pd.DataFrame([l for l in evos.split(sep='\n')][1:-1])
evos_df[['preevo', 'postevo']] = evos_df[0].str.split('->', expand=True)
evos_df['postevo'] = evos_df['postevo'].str.replace(' and ',';')
evos_df['postevo'] = evos_df['postevo'].str.replace(', ',';')
evos_df = evos_df.drop(columns=0)
evos_df['preevo'] = evos_df['preevo'].str.strip()
evos_df['postevo'] = evos_df['postevo'].str.strip()

# mons
mons_df = pd.read_csv(io.StringIO(mons.replace('Pokemon Base Stats & Types--','')), sep='|')
mons_df.columns = mons_df.columns.str.strip()
mons_df[mons_df.select_dtypes('object').columns] = mons_df[mons_df.select_dtypes('object').columns].apply(lambda x: x.str.strip())
mons_df[['TYPE1', 'TYPE2']] = mons_df['TYPE'].str.split('/', expand=True)

# tm compatibility
tmcompat_df = pd.read_csv(io.StringIO(tmcompat.replace('TM Compatibility--','')), sep='|', header=None)
tmcompat_df[['NUM', 'NAME']] = tmcompat_df[0].str.strip().str.split(' ', n=1, expand=True)
tmcompat_df = tmcompat_df.map(lambda x: x.strip() if isinstance(x, str) else x)

# moves
moves_df = moves.replace('Pokemon Movesets--\n', '').split('\n\n')
moves_df = pd.DataFrame(moves_df).rename(columns={0:'mon'})
moves_df = moves_df.apply(lambda x: x['mon'].split('\n'), axis=1)
moves_df = pd.DataFrame(moves_df.values.tolist()).add_prefix('col_')
moves_df.drop(columns=moves_df.columns[1:7], inplace=True)
moves_regex = r"(?P<num>\d+)+\s+(?P<mon>\S+)+\s[->]+\s+(?P<evo>.+)?"
moves_label = moves_df['col_0'].str.extract(moves_regex)
moves_df = pd.concat([moves_label, moves_df], axis=1).drop(columns='col_0')
moves_df.iloc[:, 3:] = moves_df.iloc[:, 3:].where(moves_df.iloc[:, 3:].apply(lambda x: x.str.startswith('Level')))
moves_df['evo'] = moves_df['evo'].replace('(no evolution)', '')
moves_df.dropna(axis=1, how='all', inplace=True)

# tms
tm_regex = r"(?P<tmnum>\w+)+\s+(?P<move>.*)"
tms_df = pd.DataFrame(parser(tms, tm_regex, '\n')[1:])
tms_df['tmnum'] = tms_df['tmnum'].str.replace('TM', '').astype(int)

# trainers
trainer_regex = r"#(?P<number>[0-9]+)\s\((?P<name>[ï\-ç♂♀\&A-Z0-9\sa-z\é\~\[\]]*)\=\>\s[-ïç♂♀a-zA-Z\s\&]*\)\s\-\s(?P<team>.+)"
trainer_df = pd.DataFrame(parser(trainer, trainer_regex, '\n'))
# team_regex = r"(?P<name>\S+)+\s+Lv(?P<level>[0-9]+)"
trainer_team = trainer_df['team'].str.split(',', expand=True)
for (index, colname) in enumerate(trainer_team):
    new_col1 = 'pkmn_' + str(colname + 1)
    new_col2 = 'lvl_' + str(colname + 1)
    trainer_team[[new_col1, new_col2]] = trainer_team[colname].str.split(' Lv', expand=True)
    trainer_team.drop(columns=colname, inplace=True)
trainer_df = pd.concat([trainer_df, trainer_team], axis=1).drop(columns='team')
trainer_df = trainer_df.map(lambda x: x.strip() if isinstance(x, str) else x)

# wilds
wilds_df = pd.DataFrame(wildmons.replace('Wild Pokemon--\n', '').split('\n\n')).rename(columns={0:'set'})
wilds_df = wilds_df['set'].str.split('\n', expand=True)
wilds_df[['set', 'loc']] = wilds_df[0].str.split('-', expand=True)
wilds_df.drop(columns=0, inplace=True)
for (index, colname) in enumerate(wilds_df.iloc[:, 0:12]):
    new_col1 = 'pkmn_' + str(colname)
    new_col2 = 'lvl_' + str(colname)
    wilds_df[colname] = wilds_df[colname].str[0:24].str.strip()
    wilds_df[[new_col1, new_col2]] = wilds_df[colname].str.split(' Lv', expand=True)
    wilds_df.drop(columns=colname, inplace=True)

# joins for easier event handling later
pokemon = pd.merge(mons_df, evos_df, how = 'left', left_on='NAME', right_on='preevo').drop(columns='preevo').rename(columns={'postevo':'EVOLUTION'})
pokemon = pd.merge(pokemon, moves_df, how='left', left_on='NAME', right_on='mon').drop(columns=['num', 'mon', 'evo'])
pokemon.columns = pokemon.columns.str.replace('col_', 'move_')
pokemon['EVOLUTION'] = pokemon['EVOLUTION'].fillna('')


# charting stats
def statchart(mon):
    base = 50
    i = 0
    stat = ['HP', 'ATK', 'DEF', 'SATK', 'SDEF', 'SPD']
    for s in mon[3:9]:
        x1 = 70 + (40 * i)
        y1 = base
        x2 = 100 + (40 * i)
        y2 = base + (s * .5)
        if s >= 180:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='green', fill_color='green')
        elif s <= 40:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='red', fill_color='red')
        else:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='white', fill_color='white')
        graph.DrawText(stat[i], location=((x1 + x2)/2, base-2), color='white', text_location=sg.TEXT_LOCATION_TOP, font=('Franklin Gothic Medium', 12))
        graph.DrawText(s, location=((x1 + x2)/2, y2+2), color='white', text_location=sg.TEXT_LOCATION_BOTTOM, font=('Franklin Gothic Medium', 12))
        i += 1

    graph.DrawText(f'{mon.iloc[1]} ({sum(mon.iloc[3:9])} BST)', location=(70, base+180), color='#f0f080', text_location=sg.TEXT_LOCATION_TOP_LEFT, font=('Franklin Gothic Medium', 16))
    graph.DrawLine(point_from=(65,base), point_to=(305,base), color='white')


def movelist(mon, logmoves = [], mvlist = []):
    mon = mon.to_list()
    i = 0
    logmoves = []
    logmoves.append([sg.Text(f'Moveset:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
    mvlist = []
    while i < len(mon):
        if str(mon[i]) != 'nan':
            mon[i] = str(mon[i]).replace('Level ', '')
            logmoves.append([sg.Text(mon[i], text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-', visible = True, pad=(0,0,0,0))])
            mvlist.append(mon[i])
        else:
            logmoves.append([sg.Text('', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-', pad=(0,0,0,0))])
        i += 1
    return logmoves, mvlist


def abillist(mon):
    alist = mon[['ABILITY1', 'ABILITY2', 'ABILITY3']]
    logabils = []
    logabils.append([sg.Text(f'Abilities:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
    i = 0
    while i < len(alist):
        if i == 2:
            logabils.append([sg.Text(f'{alist.iloc[i]} (HA)', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-al{i}-', visible = True)])
        else:
            logabils.append([sg.Text(alist.iloc[i], text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-al{i}-', visible = True)])
        i += 1
    return logabils, alist


def evolist(mon):
    logevos = []
    elist = mon['EVOLUTION']
    logevos.append([sg.Text(f'Evolutions:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
    if elist == '':
        logevos.append([sg.Text(f'None', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
        elist = 'None'
    elif elist.count(';') in (1, 2):
        elist = elist.replace(';', '\n')
        logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
    elif elist.count(';') > 2:
        i = 0
        x = elist.count(';')
        while i < x:
            elist = elist.replace(';', ', ', 1)
            elist = elist.replace(';', ',\n', 1)
            i += 2
        logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-evos-', visible = True)])
    else:
        logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
    return logevos, elist

def tmlist(mon, game):
    logtms1, logtms4, logtmsfull, tmtext, tmtextfull = [], [], [], [], []
    tmdict, tmdictfull = {}, {}
    if game == 'XY':
        gymtmlist = [83, 39, 98, 86, 24, 99, 4, 13]
    elif game == 'ORAS':
        gymtmlist = [39, 8, 72, 50, 67, 19, 4, 31] #TM31 is 
    elif game == 'SM':
        gymtmlist = [4, 13, 24, 39, 83, 86, 98, 99]
    elif game == 'USUM':
        gymtmlist = [1, 19, 54, 43, 67, 29, 66]
    logtms1.append([sg.Text(f'Leader TMs:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
    i,j = 0,0
    while i < len(gymtmlist):
        if tmcompat_df.iloc[mon.iloc[0]-1, gymtmlist[i]] == '-':
            logtms1.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm1{i}-', visible = True)])
            logtms4.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm4{i}-', visible = True)])
            tmdict[f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}'] = False
        else:
            logtms1.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='green', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm1{i}-', visible = True)])
            logtms4.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='green', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm4{i}-', visible = True)])
            tmdict[f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}'] = True
        tmtext.append(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}')
        i += 1
    while j < 100: # 100 TMs in both gens 6 and 7, there are HMs in the list so need to use flat number
        if tmcompat_df.iloc[mon.iloc[0]-1, j + 1] == '-':
            logtmsfull.append([sg.Text(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-fulltm{j}-', visible = True)])
            tmdictfull[f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}'] = False
        else:
            logtmsfull.append([sg.Text(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}', text_color='green', font=('Franklin Gothic Medium', 10), key = f'-log-fulltm{j}-', visible = True)])
            tmdictfull[f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}'] = True
        tmtextfull.append(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}')
        j += 1
    return logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull


graph=sg.Graph(canvas_size=(380,200), graph_bottom_left=(50,10), graph_top_right=(330,240),background_color='black', enable_events=True, key='-log-graph-')

r = np.random.randint(0,776)
# r = 165
logmoves, mvlist = movelist(pokemon.iloc[r,16:])
logabils, alist = abillist(pokemon.iloc[r])
logevos, elist = evolist(pokemon.iloc[r])
logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[r], game)

bwidth = 1
bpad = (1,1,0,0)
navbar = {}
if gen == 6:
    bfont = ('Franklin Gothic Medium', 12)
    for i in range(1, 7):
        navbar[i]=[[
            sg.Text(' Pokemon ', enable_events=True, key=f'-lognav-pkmn{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' Trainers ', enable_events=True, key=f'-lognav-trainer{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' Pivots ', enable_events=True, key=f'-lognav-pivot{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' TMs ', enable_events=True, key=f'-lognav-tm{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            # sg.Text(' Info ', enable_events=True, key=f'-lognav-info{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
            # sg.Text(' Search ', enable_events=True, key=f'-lognav-search{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
            sg.Text(' Random ', enable_events=True, key=f'-lognav-random{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
        ]]
elif gen == 7: # not complete, will need to fill in later
    bfont = ('Franklin Gothic Medium', 10) # need smaller font because more nav bar things, may choose to go to two rows instead but we'll see if thats needed (hopefully not), could also use abbreviations; might also roll tutor into TM for gen 7
    for i in range(1, 8):
        navbar[i]=[[
            sg.Text(' Pokemon ', enable_events=True, key=f'-lognav-pkmn{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' Trainers ', enable_events=True, key=f'-lognav-trainer{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' Pivots ', enable_events=True, key=f'-lognav-pivot{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            sg.Text(' TMs ', enable_events=True, key=f'-lognav-tm{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            # sg.Text(' Tutors ', enable_events=True, key=f'-lognav-tutor{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
            # sg.Text(' Info ', enable_events=True, key=f'-lognav-info{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
            # sg.Text(' Search ', enable_events=True, key=f'-lognav-search{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
            sg.Text(' Random ', enable_events=True, key=f'-lognav-random{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
        ]]


brcol1 = [[
    sg.Column([
        [sg.Column(logtms1, size=(150,220)),],
        [sg.Column(logabils, size=(170,120))],
    ])
]]
blcol1 = [[
    sg.Column([
        [sg.Column(logmoves, scrollable=True, vertical_scroll_only=True, size=(150,220)),],
        [sg.Column(logevos, size=(170,120))],
    ])
]]

layout_pkmn = [
    [sg.Column(navbar[1], key='-log-navbar1-', size=(340,35), justification='c')],
    [graph], 
    [
        sg.Column(blcol1, key='-log-blcol-', size=(170,350), pad=(5,0,0,0)),
        sg.Column(brcol1, key='-log-brcol-', size=(170,350), pad=(5,0,0,0))
    ],
]

layout_trainers = [
    [sg.Column(navbar[2], key='-log-navbar2-', size=(340,35), justification='c')],
]

layout_pivots = [
    [sg.Column(navbar[3], key='-log-navbar3-', size=(340,35), justification='c')],
]

layout_tms = [
    [sg.Column(navbar[4], key='-log-navbar4-', size=(340,35), justification='c')],
    [sg.Text(f'{pokemon.iloc[r,1]} ({sum(pokemon.iloc[r,3:9])} BST)', font=('Franklin Gothic Medium', 16), text_color='#f0f080', key='-log-tmpkmn-')],
    [
        sg.Text(f'Gym TMs:', font=('Franklin Gothic Medium', 14), text_color='#f0f080', size=15),
        sg.Text(f'All TMs:', font=('Franklin Gothic Medium', 14), text_color='#f0f080'),
    ],
    [sg.Column([
        [
            sg.Column(logtms4, size=(150,400)),
            sg.Column(logtmsfull, size=(150,400), scrollable=True, vertical_scroll_only=True),
        ],
    ])]
]
# layout_tutors = [
#     [sg.Column(navbar[5], key='-log-navbar4-', size=(340,35), justification='c')],
# ]
# layout_info = [
#     [sg.Column(navbar[6], key='-log-navbar4-', size=(340,35), justification='c')],
# ]
# layout_search = [
#     [sg.Column(navbar[7], key='-log-navbar4-', size=(340,35), justification='c')],
# ]

layout = [[
    sg.Column(layout_pkmn, key='-layout1-'), 
    sg.Column(layout_trainers, key='-layout2-', visible=False), 
    sg.Column(layout_pivots, key='-layout3-', visible=False), 
    sg.Column(layout_tms, key='-layout4-', visible=False), 
]]

window = sg.Window('Log reader test', layout, track_size, finalize=True, element_padding=(1,1,0,0))

statchart(pokemon.iloc[r])
logmoves, mvlist = movelist(pokemon.iloc[r,16:], logmoves, mvlist)
logabils, alist = abillist(pokemon.iloc[r])
logevos, elist = evolist(pokemon.iloc[r])
logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[r], game)

l = 1 #current layout (defaults to pokemon screen)
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == f'-lognav-pkmn{l}-':
        window[f'-layout{l}-'].update(visible=False)
        l = 1
        window[f'-layout{l}-'].update(visible=True)
    if event == f'-lognav-trainer{l}-':
        window[f'-layout{l}-'].update(visible=False)
        l = 2
        window[f'-layout{l}-'].update(visible=True)
    if event == f'-lognav-pivot{l}-':
        window[f'-layout{l}-'].update(visible=False)
        l = 3
        window[f'-layout{l}-'].update(visible=True)
    if event == f'-lognav-tm{l}-':
        window[f'-layout{l}-'].update(visible=False)
        l = 4
        window[f'-layout{l}-'].update(visible=True)
    # if event == f'-lognav-tutor{l}-':
    #     window[f'-layout{l}-'].update(visible=False)
    #     l = 5
    #     window[f'-layout{l}-'].update(visible=True)
    # if event == f'-lognav-info{l}-':
    #     window[f'-layout{l}-'].update(visible=False)
    #     l = 6
    #     window[f'-layout{l}-'].update(visible=True)
    # if event == f'-lognav-search{l}-':
    #     window[f'-layout{l}-'].update(visible=False)
    #     l = 7
    #     window[f'-layout{l}-'].update(visible=True)
    if event in ('-lognav-random1-', '-lognav-random4-',): # only relevant for the pokemon and tm pages (and eventually tutor)
        i = 0
        r = np.random.randint(0,776)
        # r = 132 # testing eevee in particular
        # r = 165 # testing ledian in particular
        graph.Erase()
        statchart(pokemon.iloc[r])
        logmoves, mvlist = movelist(pokemon.iloc[r,16:], logmoves, mvlist)
        logabils, alist = abillist(pokemon.iloc[r])
        logevos, elist = evolist(pokemon.iloc[r])
        logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[r], game)
        while i < len(tmtextfull):
            if i < len(mvlist):
                window[f'-log-ml{i}-'].update(mvlist[i], visible = True)
            elif i < len(logmoves) - 1:
                window[f'-log-ml{i}-'].update(visible = False)
            if i < len(alist) and i == 2:
                window[f'-log-al{i}-'].update(f'{alist.iloc[i]} (HA)', visible = True)
            elif i < len(alist):
                window[f'-log-al{i}-'].update(alist.iloc[i], visible = True)
            if i == 0:
                window[f'-log-evos-'].update(f'{elist}', visible = True)
            if i < len(tmtext):
                if tmdict[tmtext[i]] == False:
                    window[f'-log-gymtm1{i}-'].update(text_color='white')
                    window[f'-log-gymtm4{i}-'].update(text_color='white')
                elif tmdict[tmtext[i]] == True:
                    window[f'-log-gymtm1{i}-'].update(text_color='green')
                    window[f'-log-gymtm4{i}-'].update(text_color='green')
            if tmdictfull[tmtextfull[i]] == False:
                window[f'-log-fulltm{i}-'].update(text_color='white')
            elif tmdictfull[tmtextfull[i]] == True:
                window[f'-log-fulltm{i}-'].update(text_color='green')
            i += 1
        window['-log-tmpkmn-'].update(f'{pokemon.iloc[r,1]} ({sum(pokemon.iloc[r,3:9])} BST)')
        # window.refresh()

window.close()