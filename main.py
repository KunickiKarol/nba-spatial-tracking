# %%
from Game import Game
from time import time
import pandas as pd
import math
game = Game(game_id='0021500492')
df, action_df = game.read_json()
moment_df, game_series, move_df, player_df, team_df, action_df = game.get_dfs()
# %%
game.show(82, 95)
# %%

seq_df =  moment_df.dropna(subset=['shot_clock'])
seq_df = seq_df[seq_df['shot_clock'] < 24]

start_time = 24
seq_ids = []
seq_counter = 0
for row in seq_df.itertuples():
    if row.shot_clock >= start_time:
        seq_counter += 1
    seq_ids.append(seq_counter)
    start_time = row.shot_clock
seq_df['seq_id'] = seq_ids 

def count_dist_merged(row):
    return math.sqrt(pow(row['x'] - row['x_ball'], 2) + pow(row['y'] - row['y_ball'], 2))

ball_df = move_df[move_df['object_id'] == -1]
players_df = move_df[move_df['object_id'] != -1]

merge_df = ball_df[['moment_id', 'x', 'y']]
ball_cord_names = {'x': 'x_ball', 'y': 'y_ball'}
merge_df.rename(columns=ball_cord_names, inplace=True)

players_df = pd.merge(players_df, merge_df, how='left', on='moment_id')
players_df['dist_diff'] = players_df.apply(count_dist_merged, axis=1)
idx_min_dist_diff = players_df.groupby('moment_id')['dist_diff'].idxmin()

# Tworzenie kolumny 'owner' z wartościami True dla indeksów minimalnych, False w przeciwnym razie
players_df['owner'] = False
players_df.loc[idx_min_dist_diff, 'owner'] = True

merge_df = player_df[['player_id', 'team_id']]
players_df = pd.merge(players_df, merge_df, how='left', left_on='object_id', right_on='player_id')

merge_df = seq_df[['moment_id', 'seq_id']]
players_df = pd.merge(players_df, merge_df, how='left', left_on='moment_id', right_on='moment_id')


TEAM_OWNER_THRESHOLD = 99
count_per_team = players_df.groupby(['seq_id', 'team_id'])['owner'].sum()

# Znalezienie indeksów dla maksymalnych wartości w każdej grupie 'seq_id'
idx_max_owner = count_per_team.groupby('seq_id').idxmax()

# Utworzenie DataFrame z wynikami
team_owner = pd.DataFrame(list(idx_max_owner), columns=['seq_id', 'team_id'])
team_owner['owner_count'] = count_per_team.loc[idx_max_owner].values
team_owner = team_owner[team_owner['owner_count'] > TEAM_OWNER_THRESHOLD]

# %%
move_owner_df = team_owner
move_owner_df.rename(columns={'team_id': 'attack_team'}, inplace=True)

players_seq_df = pd.merge(players_df, team_owner, how='left', on='seq_id')
players_seq_df =  players_seq_df.dropna(subset=['attack_team'])
ball_seq_df = ball_df[ball_df['moment_id'].isin(players_seq_df['moment_id'])]

# %%

def get_seq_df():
    seq_df =  moment_df.dropna(subset=['shot_clock'])
    seq_df = seq_df[seq_df['shot_clock'] < 24]
    
    start_time = 24
    seq_ids = []
    seq_counter = 0
    for row in seq_df.itertuples():
        if row.shot_clock >= start_time:
            seq_counter += 1
        seq_ids.append(seq_counter)
        start_time = row.shot_clock
    seq_df['seq_id'] = seq_ids
    return seq_df[['moment_id', 'seq_id']]

def count_dist_merged(row):
    return math.sqrt(pow(row['x'] - row['x_ball'], 2) + pow(row['y'] - row['y_ball'], 2))

def add_owner_moment(players_df, ball_df):
    merge_df = ball_df[['moment_id', 'x', 'y']]
    ball_cord_names = {'x': 'x_ball', 'y': 'y_ball'}
    merge_df.rename(columns=ball_cord_names, inplace=True)
    
    players_df = pd.merge(players_df, merge_df, how='left', on='moment_id')
    players_df['dist_diff'] = players_df.apply(count_dist_merged, axis=1)
    idx_min_dist_diff = players_df.groupby('moment_id')['dist_diff'].idxmin()
    
    # Tworzenie kolumny 'owner' z wartościami True dla indeksów minimalnych, False w przeciwnym razie
    players_df['owner'] = False
    players_df.loc[idx_min_dist_diff, 'owner'] = True

    merge_df = player_df[['player_id', 'team_id']]
    players_df = pd.merge(players_df, merge_df, how='left', left_on='object_id', right_on='player_id')
    return players_df

def get_team_owner(players_df):
    TEAM_OWNER_THRESHOLD = 99
    count_per_team = players_df.groupby(['seq_id', 'team_id'])['owner'].sum()
    
    # Znalezienie indeksów dla maksymalnych wartości w każdej grupie 'seq_id'
    idx_max_owner = count_per_team.groupby('seq_id').idxmax()
    
    # Utworzenie DataFrame z wynikami
    team_owner = pd.DataFrame(list(idx_max_owner), columns=['seq_id', 'team_id'])
    team_owner['owner_count'] = count_per_team.loc[idx_max_owner].values
    team_owner = team_owner[team_owner['owner_count'] > TEAM_OWNER_THRESHOLD]
    team_owner.rename(columns={'team_id': 'attack_team'}, inplace=True)
    return team_owner


ball_df = move_df[move_df['object_id'] == -1]
players_df = move_df[move_df['object_id'] != -1]





def set_field_time(self, players_df):
    merge_df = self.moment_df[['moment_id', 'play_time']]
    players_df = pd.merge(players_df, merge_df, how='left', on='moment_id')
    players_df['total_field_time']  = players_df.groupby('object_id')['moment_id'].diff().ne(1).cumsum().groupby(players_df['object_id']).cumcount()
    players_df['field_time'] = 0.0
    field_times_dict = {}
    total_field_times_dict = {}
    for player_id in players_df['object_id'].unique():
        player = players_df[players_df['object_id']==player_id]
        total_field_time = []
        
        field_time = []
        last_moment_player = player.iloc[0].moment_id
        start_time = player.iloc[0].play_time
        
        for player_moment in player.itertuples():
            if player_moment.moment_id - last_moment_player > 1:
                last_moment_player = player_moment.moment_id
                start_time = player_moment.play_time
                field_time.append(0.0)
            else:
                last_moment_player = player_moment.moment_id
                value = player_moment.play_time - start_time
                field_time.append(value)
                
                
            if player_moment.total_field_time == 0:
                total_start_time = player_moment.play_time
                total_field_time.append(0.0)
            else:
                value = player_moment.play_time - total_start_time
                total_field_time.append(value)
    
        field_times_dict[player_id] = field_time
        total_field_times_dict[player_id] = total_field_time
    
        
    for key, item in total_field_times_dict.items():
        players_df.loc[players_df['object_id'] == key, 'total_field_time'] = item
        
    for key, item in field_times_dict.items():
        
        players_df.loc[players_df['object_id'] == key, 'field_time'] = item
        
        
    players_df.drop('play_time', axis=1, inplace=True)
    return players_df






players_df
players_df = add_owner_moment(players_df, ball_df)
merge_df = get_seq_df()
players_df = pd.merge(players_df, merge_df, how='left', left_on='moment_id', right_on='moment_id')
# %%
def set_field_time(players_df):
    merge_df = moment_df[['moment_id', 'play_time']]
    players_df = pd.merge(players_df, merge_df, how='left', on='moment_id')
    players_df['field_time']  = players_df.groupby('object_id')['moment_id'].diff().ne(1).cumsum().groupby(players_df['object_id']).cumcount()
    field_times_dict = {}
    for player_id in players_df['object_id'].unique():
        player = players_df[players_df['object_id']==player_id]
        field_time = []

        for player_moment in player.itertuples():
            if player_moment.field_time == 0:
                start_time = player_moment.play_time
                field_time.append(0.0)
            else:
                value = player_moment.play_time - start_time
                field_time.append(value)
        field_times_dict[player_id] = field_time
        
    for key, item in field_times_dict.items():
        players_df.loc[players_df['object_id'] == key, 'field_time'] = item
        
    players_df.drop('play_time', axis=1, inplace=True)
    return players_df
# %%
#a.groupby('object_id')['play_time'].diff().where(a['field_time'] == 1).head(40)

    field_times_dict[player_id] = field_time
# %%
for key, item in field_times_dict.items():
    a.loc[a['object_id'] == key, 'field_time'] = item

        
    
# %%
field_times_dict[202685]











    