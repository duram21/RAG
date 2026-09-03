# OP.GG MCP 도구 레퍼런스

`python project/gen_tools_doc.py` 로 서버 스키마에서 자동 생성됩니다.
직접 고치지 마세요 — 다시 생성하면 사라집니다.

## 쓰는 법

```python
import importlib.util
spec = importlib.util.spec_from_file_location('opgg', 'project/opgg-api.py')
opgg = importlib.util.module_from_spec(spec); spec.loader.exec_module(opgg)

client = opgg.MCPClient()
client.connect()                      # 반드시 먼저 호출
data = client.call_tool('도구이름', {인자들})
```

## 응답 형식이 두 가지입니다

| 표시 | 조건 | 형태 |
|---|---|---|
| **압축** | `desired_output_fields` 를 받는 도구 | `class ...` 선언 + 위치 인자. `call_tool` 이 dict 로 변환해서 돌려줍니다 |
| **JSON** | 그 외 | 평범한 JSON |

`desired_output_fields` 는 **닫힌 집합**입니다. 각 도구의 '출력 필드' 목록에 있는 것만 쓸 수 있고, 없는 이름을 지어내면 거부됩니다.

## 챔피언 표기법이 도구마다 다릅니다

| 인자 이름 | 표기 | 예시 |
|---|---|---|
| `champions` (배열) | 내부 코드명 | `Garen`, `MonkeyKing` |
| `champion`, `my_champion`, `opponent_champion` | 대문자+언더바 | `GAREN`, `MONKEY_KING` |

내부 코드명은 `python project/opgg-api.py --champions` 로 확인하세요.

---

# 리그 오브 레전드  (17개)

## `lol_esports_list_schedules`

> Returns LoL esports schedules or results. Args: mode="schedule" for future schedules from today, mode="result" for latest completed match results beyond the old 7-day window, optional league such as "lck", "kespa", "ewc", "msi", or "worlds", optional team_name such as "T1", and optional limit up to 50 for result mode. Results include teams, leagues, scores, and match times in ISO 8601 UTC format. Always convert to user's timezone before presenting.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `league` | string | 선택 | `lck` \| `kespa` \| `ewc` \| `lpl` \| `lec` \| `lcs` \| `ljl` \| `vcs` \| `cblol` \| `lcl` \| `lla` \| `tcl` \| `pcs` \| `lco` \| `lta south` \| `lta north` \| `lcp` \| `first stand` \| `fst` \| `al` \| `msi` \| `worlds` \| `lta` | Optional LoL esports league/tournament short name such as "lck", "kesp |
| `limit` | integer | 선택 | 기본값 `50` | Optional maximum completed result matches to return in result mode (de |
| `mode` | string | 선택 | `schedule` \| `result` | Use "schedule" for upcoming/future match schedules from today, or "res |
| `team_name` | string | 선택 |  | Optional esports team name or acronym to filter schedules/results, e.g |

---

## `lol_esports_list_team_standings`

> Returns the latest team standings for the requested LoL league.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `short_name` | string | **필수** | lck, kespa, ewc |  |

---

## `lol_get_champion_analysis`

> Returns detailed champion stats (win/pick/ban rates), optimal builds (items, runes, skills, spells), skill combos, counter matchups, and team synergies for a specific champion and position. MUST call when user mentions any champion, asks for item/skill recommendations, gameplay tips, or matchup strategies. Counter picks available in weak_counters field; each counter includes my_win_rate and counter_win_rate for the head-to-head matchup. Infer position from context if not specified.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion` | string | **필수** | ANNIE, OLAF, GALIO | Champion name in UPPER_SNAKE_CASE |
| `game_mode` | string | **필수** | `ranked` \| `flex` \| `urf` \| `aram` \| `nexus_blitz` | Game mode |
| `position` | string | **필수** | `all` \| `none` \| `top` \| `mid` \| `jungle` \| `adc` \| `support` | Lane position |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `tier` | string | 선택 | all, challenger, grandmaster | Rank tier filter for matchup/build stats. Omit for all-tier aggregate  |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
champion
data.boots.{ids[],ids_names[],pick_rate,play,win}
data.core_items.{ids[],ids_names[],pick_rate,play,win}
data.fifth_items[].{ids[],ids_names[],pick_rate,play,win}
data.fourth_items[].{ids[],ids_names[],pick_rate,play,win}
data.last_items[].{ids[],ids_names[],pick_rate,play,win}
data.runes.{id,pick_rate,play,primary_page_id,primary_page_name,primary_rune_ids[],primary_rune_names[],secondary_page_id,secondary_page_name,secondary_rune_ids[],secondary_rune_names[],stat_mod_ids[],stat_mod_names[],win}
data.sixth_items[].{ids[],ids_names[],pick_rate,play,win}
data.skill_combos[].{name,video_url}
data.skill_masteries.builds[].{order[],pick_rate,play,win}
data.skill_masteries.{ids[],pick_rate,play,win}
data.skills.{order[],pick_rate,play,win}
data.starter_items.{ids[],ids_names[],pick_rate,play,win}
data.strong_counters[].{champion_id,champion_name,counter_win_rate,my_win_rate,play,win,win_rate}
data.summary.average_stats.tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.summary.average_stats.{ban_rate,kda,pick_rate,play,rank,tier,win_rate}
data.summary.positions[].counters[].{champion_id,champion_name,play,win}
data.summary.positions[].name
data.summary.positions[].roles[].name
data.summary.positions[].roles[].stats.{play,role_rate,win,win_rate}
data.summary.positions[].stats.tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.summary.positions[].stats.{ban_rate,kda,pick_rate,play,role_rate,win_rate}
data.summary.{id,is_rip,is_rotation,roles}
data.summoner_spells.{ids[],ids_names[],pick_rate,play,win}
data.synergies.adc[].synergy_tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.synergies.adc[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}
data.synergies.jungle[].synergy_tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.synergies.jungle[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}
data.synergies.mid[].synergy_tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.synergies.mid[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}
data.synergies.support[].synergy_tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.synergies.support[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}
data.trends.ban.{created_at,rank,rate,version}
data.trends.pick.{created_at,rank,rate,version}
data.trends.win.{created_at,rank,rate,version}
data.trends.{total_position_rank,total_rank}
data.weak_counters[].{champion_id,champion_name,counter_win_rate,my_win_rate,play,win,win_rate}
data.{damage_type,mythic_items}
position
```

</details>

---

## `lol_get_champion_synergies`

> Returns synergy recommendations (win rate + role fit) for your champion and the ally lane you specify.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion` | string | **필수** | ANNIE, OLAF, GALIO | Your champion |
| `my_position` | string | **필수** | `all` \| `none` \| `top` \| `mid` \| `jungle` \| `adc` \| `support` | Your position |
| `synergy_position` | string | **필수** | `all` \| `none` \| `top` \| `mid` \| `jungle` \| `adc` \| `support` | The position you want synergy recommendations for (teammate position) |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
champion
data.synergies[].synergy_tier_data.{rank,rank_prev,rank_prev_patch,tier}
data.synergies[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}
lang
my_position
synergy_position
```

</details>

---

## `lol_get_lane_matchup_guide`

> Provides lane matchup guidance for your champion versus a named opponent, including position-specific tips, runes, and item timings.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `my_champion` | string | **필수** | ANNIE, OLAF, GALIO | Champion name in UPPER_SNAKE_CASE |
| `opponent_champion` | string | **필수** | ANNIE, OLAF, GALIO | Champion name in UPPER_SNAKE_CASE |
| `position` | string | **필수** | `all` \| `none` \| `top` \| `mid` \| `jungle` \| `adc` \| `support` | Lane position (top, mid, jungle, adc, support) |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |

---

## `lol_get_pro_player_riot_id`

> Looks up a pro player alias and returns their Riot ID plus team/region metadata so you can link their OP.GG profile.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `player_name` | string | **필수** |  | Nickname, alias, or real name fragment of the pro player (e.g., Faker, |
| `region` | string | **필수** | KR, BR, EUNE | League region to constrain the lookup. |
| `return_suggestions` | boolean | 선택 | 기본값 `False` | Set true to include close matches when the exact alias is not found. |

---

## `lol_get_summoner_game_detail`

> Returns full match detail (teams, participants, builds, bans) for a specific game id whenever the user drills into a single match. When the question is about one summoner's performance, also pass focus_riot_id ("gameName#tagLine"): the matching participant is flagged is_target=true — read the focused summoner's numbers from the participant row where is_target is true, never from a neighbouring participant. If no unique match is found, no row is flagged and data.game_detail.focus_error explains why.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `created_at` | string | **필수** |  | Match creation timestamp (ISO-8601). |
| `game_id` | string | **필수** |  | Unique identifier for the target match. |
| `region` | string | **필수** | KR, BR, EUNE | Server region code |
| `focus_riot_id` | string | 선택 |  | Riot ID ('gameName#tagLine') of the summoner the user is asking about. |
| `game_name` | string | 선택 |  | Riot ID game name before the "#" of the summoner being investigated (e |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `tag_line` | string | 선택 |  | Riot ID tag line following the "#" (e.g., "KR1" from "Faker#KR1"). |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.game_detail.average_tier_info.{border_image_url,division,tier}
data.game_detail.teams[].game_stat.{atakhan_kill,baron_kill,champion_first,champion_kill,dragon_kill,gold_earned,horde_kill,inhibitor_kill,is_win,rift_herald_kill,tower_kill}
data.game_detail.teams[].participants[].rune.{primary_page_id,primary_rune_id,secondary_page_id}
data.game_detail.teams[].participants[].stats.op_score_timeline_analysis.{last,left,right}
data.game_detail.teams[].participants[].stats.{assist,champion_level,death,gold_earned,kill,largest_critical_strike,largest_killing_spree,largest_multi_kill,minion_kill,neutral_minion_kill,neutral_minion_kill_enemy_jungle,neutral_minion_kill_team_jungle,op_score,op_score_rank,result,time_ccing_others,total_damage_dealt_to_champions,total_damage_taken,total_heal,vision_wards_bought_in_game,ward_place}
data.game_detail.teams[].participants[].summoner.player.{esports_url,nickname,real_name}
data.game_detail.teams[].participants[].summoner.{game_name,puuid,tagline}
data.game_detail.teams[].participants[].{champion_id,champion_name,is_target,items[],items_names[],position,role_bound_item,spells[],team_key}
data.game_detail.teams[].{banned_champions[],banned_champions_names[],key}
data.game_detail.{clips,created_at,game_length_second,game_map,game_type,id}
```

</details>

---

## `lol_get_summoner_profile`

> Returns summoner profile with rank, tier, LP, win rate, and champion pool. MUST call for identity/profile/rank queries. DO NOT call for match history. Ask for region if not found.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `game_name` | string | **필수** |  | Riot ID game name before the "#" (e.g., "Faker" from "Faker#KR1") |
| `region` | string | **필수** | KR, BR, EUNE | Server region code |
| `tag_line` | string | **필수** |  | Riot ID tag line following the "#" (e.g., "KR1" from "Faker#KR1") |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.summoner.current_season_high_tiers.rank_entries[].game_type
data.summoner.current_season_high_tiers.rank_entries[].high_rank_info.{created_at,division,elo,lose,lp,tier,win}
data.summoner.current_season_high_tiers.season_id
data.summoner.highlight_info.scene_type[].{events[],mode}
data.summoner.highlight_info.{created_at,deleted_at,platform_id,puuid,summoner_id,user_type}
data.summoner.ladder_rank.{rank,total}
data.summoner.league_stats[].high_leagues[].{current_count,demotion_candidate_count,key,lp_threshold,promotion_candidate_count}
data.summoner.league_stats[].match_record.{lose,play,win}
data.summoner.league_stats[].tier_info.{border_image_url,division,level,lp,tier,tier_image_url}
data.summoner.league_stats[].{game_type,is_fresh_blood,is_hot_streak,is_inactive,is_veteran,lose,series,updated_at,win}
data.summoner.lp_histories[].tier_info.{border_image_url,division,level,lp,tier,tier_image_url}
data.summoner.lp_histories[].{created_at,elo_point}
data.summoner.most_champions.champion_stats[].{assist,champion_name,damage_dealt_to_champions,damage_taken,death,double_kill,game_length_second,gold_earned,id,kill,lose,minion_kill,neutral_minion_kill,op_score,penta_kill,play,quadra_kill,snowball_hits,snowball_throws,triple_kill,vision_wards_bought_in_game,win}
data.summoner.most_champions.{game_type,lose,play,season_id,win,year}
data.summoner.player.current_pro_team.pro_team.{acronym,cover_images,ended_at,esports_url,id,image_url,image_url_dark_mode,image_url_light_mode,is_active,league_id,name,nationality,short_name,started_at,type}
data.summoner.player.current_pro_team.{ended_at,is_starter,position,role,started_at}
data.summoner.player.{birth_country_code,birthdate,channels,esports_url,id,nationality_country_code,nickname,pro_team_careers,real_name}
data.summoner.previous_season_tiers[].rank_entries[].game_type
data.summoner.previous_season_tiers[].rank_entries[].high_rank_info.{created_at,division,elo,lose,lp,tier,win}
data.summoner.previous_season_tiers[].rank_entries[].rank_info.{created_at,division,elo,lose,lp,tier,win}
data.summoner.previous_season_tiers[].season_id
data.summoner.previous_seasons[].season_id
data.summoner.previous_seasons[].tier_info.{border_image_url,division,level,lp,tier,tier_image_url}
data.summoner.ranked_most_champions.my_champion_stats[].basic.{ace,assist,cs,damage_distribution,damage_participation,damage_to_champion,death,double_kill,double_kill_play,gold,kill,kill_participation,lane_lead,lane_score,lane_score_count,mvp,op_score,op_score_rank,penta_kill,penta_kill_play,quadra_kill,quadra_kill_play,triple_kill,triple_kill_play,vision_score,vision_ward,ward_kill,ward_placed}
data.summoner.ranked_most_champions.my_champion_stats[].extend.{buff_steal,cc,cc_make_kill,cc_score,damage_self_mitigated,damage_taken,damage_to_building,damage_to_objective,damage_to_turret,enemy_jungle_monster_kill,epic_monster_kill_near_enemy_jungler,epic_monster_steal_no_smite,evolution_first,evolution_none,evolution_second,faster_support_quest,heal,heal_to_team,inhibitor_kill,initial_crab_kill,invade_kill,invade_kill_play,invade_play,jungle_cs_10_minute,lane_advantage_7_minute,lane_cs_10_minute,magic_damage_to_champion,make_solo_kill,neutral_cs,object_steal,physical_damage_to_champion,save_ally,shield_to_team,solo_kill,true_damage_to_champion,turret_kill,turret_plate,ward_guard}
data.summoner.ranked_most_champions.my_champion_stats[].{champion_name,game_second,id,lose,play,win}
data.summoner.ranked_most_champions.{game_type,lose,play,season_id,win}
data.summoner.recent_champion_stats[].{assist,champion_name,death,id,kill,play,win}
data.summoner.{acct_id,game_name,has_highlight,id,internal_name,level,name,profile_image_url,puuid,recent_videos_added_count,region,renewable_at,revision_at,summoner_id,tagline,updated_at}
```

</details>

---

## `lol_list_aram_augments`

> Returns ARAM augment stats for a champion with localized names and descriptions. Only tier 3 or higher augments are included.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion_id` | integer | 선택 |  | League of Legends champion ID (for example, 81 for Ezreal). |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
champion_id
data.augments[].{desc,id,name,performance,popular,tier}
lang
```

</details>

---

## `lol_list_champion_details`

> Returns ability, tip, lore, and stat metadata for up to 10 champions (skins/media trimmed for smaller payloads).

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champions` | string[] | 선택 | 기본값 `['AHRI', 'YASUO', 'LUX']` | Array of champion names in UPPER_SNAKE_CASE |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.champions[].info.{attack,defense,difficulty,magic}
data.champions[].passive.{description,name}
data.champions[].spells[].{cooldown_burn[],cooldown_burn_float[],cost_burn[],description,key,max_rank,name,range_burn[],tooltip}
data.champions[].stats.{armor,armorperlevel,attackdamage,attackdamageperlevel,attackrange,attackspeed,attackspeedperlevel,crit,critperlevel,hp,hpperlevel,hpregen,hpregenperlevel,movespeed,mp,mpperlevel,mpregen,mpregenperlevel,spellblock,spellblockperlevel}
data.champions[].{ally_tips[],blurb,enemy_tips[],id,key,lore,name,partype,release_date,tags[],title}
lang
requested_champions[]
```

</details>

---

## `lol_list_champion_leaderboard`

> Lists the top master+ players for a champion/region so you can study their builds and match stats.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion` | string | **필수** | ANNIE, OLAF, GALIO | Champion name in UPPER_SNAKE_CASE |
| `region` | string | **필수** | KR, BR, EUNE | Server region code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
champion
leaderboard[].most_champion_stat.{assist,damage_dealt_to_champions,damage_taken,death,double_kill,game_length_second,gold_earned,id,kill,lose,minion_kill,neutral_minion_kill,op_score,penta_kill,play,quadra_kill,snowball_hits,snowball_throws,triple_kill,vision_wards_bought_in_game,win}
leaderboard[].rank
leaderboard[].summoner.league_stats[].tier_info.{border_image_url,division,level,lp,tier,tier_image_url}
leaderboard[].summoner.league_stats[].{game_type,is_fresh_blood,is_hot_streak,is_inactive,is_veteran,lose,series,updated_at,win}
leaderboard[].summoner.{acct_id,game_name,id,internal_name,level,most_champions,name,player,profile_image_url,puuid,summoner_id,tagline,updated_at}
region
```

</details>

---

## `lol_list_champions`

> Returns every champion's id, key, name, and release date in the requested language.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.champions[].{champion_id,key,name,release_date}
lang
```

</details>

---

## `lol_list_discounted_skins`

> Retrieves information about champion skins that are currently on sale.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion` | string | 선택 | ANNIE, OLAF, GALIO | Optional. Champion name in UPPER_SNAKE_CASE. If provided, only returns |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data[].{champion_id,champion_key,champion_name,cost,currency,discount_rate,ended_at,skin_id,skin_name,started_at}
lang
```

</details>

---

## `lol_list_items`

> Returns localized items (ids, names, descriptions, build trees, gold costs) filtered by map (default Summoner's Rift).

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `map` | string | 선택 | `SUMMONERS_RIFT` \| `HOWLING_ABYSS` \| `NEXUS_BLITZ` \| `TEAMFIGHT_TACTICS` \| `ARENA_MAP_1` | Map identifier (SUMMONERS_RIFT, HOWLING_ABYSS, NEXUS_BLITZ, TEAMFIGHT_ |

---

## `lol_list_lane_meta_champions`

> Returns lane-by-lane champion tiers with win/pick/ban rates, KDA, and tier rankings. Tier 1 champions are OP and easy to play - recommend them for strong picks. Filter by position or use "all" for every lane.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `position` | string | 선택 | `all` \| `none` \| `top` \| `mid` \| `jungle` \| `adc` \| `support` | Lane position (top, mid, jungle, adc, support) |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.positions.adc[].{ban_rate,champion,is_rip,kda,kill,pick_rate,play,rank,rank_prev,rank_prev_patch,role_rate,tier,win,win_rate}
data.positions.jungle[].{ban_rate,champion,is_rip,kda,kill,pick_rate,play,rank,rank_prev,rank_prev_patch,role_rate,tier,win,win_rate}
data.positions.mid[].{ban_rate,champion,is_rip,kda,kill,pick_rate,play,rank,rank_prev,rank_prev_patch,role_rate,tier,win,win_rate}
data.positions.support[].{ban_rate,champion,is_rip,kda,kill,pick_rate,play,rank,rank_prev,rank_prev_patch,role_rate,tier,win,win_rate}
data.positions.top[].{ban_rate,champion,is_rip,kda,kill,pick_rate,play,rank,rank_prev,rank_prev_patch,role_rate,tier,win,win_rate}
lang
position_filter
```

</details>

---

## `lol_list_skin_stats_for_champion`

> Lists a champion's skins in popularity rank order. Default ranking is by play count (1 = most played in real matches) — the natural answer for ambiguous popularity questions like "which Aatrox skin is most popular?". Pass sort_by="ownership" ONLY when the user explicitly asks about ownership/possession (e.g., "보유 기준", "가지고 있는 사람 많은 순", "owned by most", "collection-wise", "가장 많이 갖고 있는 스킨"). Internal raw counts are NOT exposed in either mode — only rank position and skin identity. Base skin is always excluded since it inherits every match where no other skin was equipped (play mode) and is universally owned by default (ownership mode).

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion` | string | **필수** | ANNIE, OLAF, GALIO | Required. Champion name in UPPER_SNAKE_CASE (e.g., AATROX, YASUO). |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code used to localize skin names. |
| `sort_by` | string | 선택 | `play` \| `ownership` | Ranking metric. "play" (default) = how many games each skin was actual |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
champion_id
champion_key
champion_name
data[].{rank,skin_id,skin_name}
lang
```

</details>

---

## `lol_list_summoner_matches`

> Returns recent match history with per-game stats for the target summoner only (excludes enemy stats). MUST call for match history, performance analysis, or improvement tips. DO NOT call for profile/rank queries. Use lol_get_summoner_game_detail for full game details with all players.

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `game_name` | string | **필수** |  | Riot ID game name before the "#" (e.g., "Faker" from "Faker#KR1") |
| `region` | string | **필수** | KR, BR, EUNE | Server region code |
| `tag_line` | string | **필수** |  | Riot ID tag line following the "#" (e.g., "KR1" from "Faker#KR1") |
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |
| `limit` | integer | 선택 |  | Maximum number of matches to return. |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
data.game_history[].average_tier_info.{border_image_url,division,tier}
data.game_history[].clips[].{asset,puuid,status,unavailable_code,use_case}
data.game_history[].participants[].rune.{primary_page_id,primary_rune_id,secondary_page_id}
data.game_history[].participants[].stats.op_score_timeline[].{score,second}
data.game_history[].participants[].stats.op_score_timeline_analysis.{last,left,right}
data.game_history[].participants[].stats.{assist,champion_level,death,gold_earned,kill,largest_critical_strike,largest_killing_spree,largest_multi_kill,minion_kill,neutral_minion_kill,neutral_minion_kill_enemy_jungle,neutral_minion_kill_team_jungle,op_score,op_score_rank,result,time_ccing_others,total_damage_dealt_to_champions,total_damage_taken,total_heal,vision_wards_bought_in_game,ward_place}
data.game_history[].participants[].summoner.player.{esports_url,nickname,real_name}
data.game_history[].participants[].summoner.{game_name,profile_image_url,puuid,tagline}
data.game_history[].participants[].{champion_id,champion_name,items[],items_names[],position,role_bound_item,spells[],team_key}
data.game_history[].teams[].game_stat.{atakhan_kill,baron_kill,champion_first,champion_kill,dragon_kill,gold_earned,horde_kill,inhibitor_kill,is_win,rift_herald_kill,tower_kill}
data.game_history[].teams[].{banned_champions[],banned_champions_names[],key}
data.game_history[].{created_at,game_length_second,game_map,game_type,id}
```

</details>

---

# 전략적 팀 전투(TFT)  (6개)

## `tft_get_champion_item_build`

> TFT tool for retrieving champion item build information.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `champion_id` | string | **필수** | `DA_18_ElderDragon` \| `DA_18_Morgana` \| `DA_18_Aphelios` \| `DA_Cinderling18` \| `DA_18_Tristana` \| `DA_18_MasterYi_AD` \| `DA_18_GnarSmall` \| `DA_Lux18_Blackthorn` \| `DA_18_LeBlanc` \| `DA_KogMaw18_AD` \| `DA_18_Veigar` \| `DA_18_Elise` \| `DA_18_Sentry` \| `DA_18_Varus` \| `DA_18_Ivern` \| `DA_18_RekSai` \| `DA_Amumu18` \| `DA_18_Ornn` \| `DA_18_Camille` \| `DA_18_Kayle` \| `DA_18_Alistar` \| `DA_18_Rakan` \| `DA_18_Lux_Coven` \| `DA_18_Rammus` \| `DA_18_Diana` \| `DA_Vi18` \| `DA_18_Xayah` \| `DA_Gromp18_AP` \| `DA_18_Ahri` \| `DA_Krug18` \| `DA_18_Zyra` \| `DA_18_Azir` \| `DA_Taric18` \| `TFT18_NidaleeCougar` \| `DA_18_Lux_Fae` \| `DA_18_Sett` \| `DA_18_Ashe` \| `DA_18_Shen` \| `DA_18_Caitlyn` \| `DA_18_Leona` \| `DA_18_Lux_Primal` \| `DA_18_Lillia` \| `DA_18_Lux_Moonbeam` \| `DA_18_Alune` \| `TFT18_SprykinSummonMelee` \| `DA_Sentinel18` \| `TFT18_Gromp` \| `DA_Fiddlesticks18` \| `DA_18_Teemo` \| `DA_Karma18` \| `DA_18_Maokai` \| `TFT18_Akali` \| `DA_Lux18_Base` \| `DA_18_Akali_AD` \| `DA_18_Lux_Sunbeam` \| `DA_18_Lux_Inferno` \| `DA_Draven18` \| `TFT18_MasterYi` \| `DA_18_Warwick` \| `DA_CrimsonRaptor18` \| `DA_18_Kobuko` \| `DA_18_Ezreal` \| `DA_18_Sivir` \| `DA_Brambleback18` \| `DA_18_Malphite` \| `DA_18_Kennen` \| `DA_18_Cassiopeia` \| `DA_18_Soraka` \| `DA_Scuttlecrab18` \| `DA_18_Rengar` \| `DA_18_Sejuani` \| `DA_Lux18_Blossom` \| `DA_18_Lux_Elderwood` \| `DA_18_EliseSpider` \| `DA_18_Hecarim` \| `TFT18_KogMaw` \| `DA_18_Yorick` \| `DA_Nidalee18_AP` \| `DA_Murkwolf18` \| `DA_18_KhaZix` \| `DA_18_Yunara` | TFT champion ID (e.g., TFT17_Riven) to retrieve item builds for. |

---

## `tft_get_play_style`

> This tool provides comments on the playstyle of TFT champions.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `puuid` | string | **필수** |  | Riot Account PUUID; a 78-character URL-safe identifier (alphanumeric w |
| `region` | string | **필수** | kr, br, eune | The TFT region code used to find the player's profile and matches. |

---

## `tft_list_augments`

> Retrieves metadata for all Teamfight Tactics augments with localized names and descriptions in a table-friendly JSON (headers/rows/header_description). Returns apiName, desc, name, tier, and imageUrl for all augments in the specified language.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |

---

## `tft_list_champions_for_item`

> TFT tool for retrieving champion recommendations for a specific item.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `item_id` | string | **필수** | `DA_18_EmblemBlackthorn` \| `DA_18_EmblemBlossom` \| `DA_18_EmblemBrawler` \| `DA_18_EmblemCoven` \| `DA_18_EmblemDefender` \| `DA_18_EmblemElderwood` \| `DA_18_EmblemExecutioner` \| `DA_18_EmblemFae` \| `DA_18_EmblemFloraFatalis` \| `DA_18_EmblemFloraFatalisAugment` \| `DA_18_EmblemHunter` \| `DA_18_EmblemInferno` \| `DA_18_EmblemInvoker` \| `DA_18_EmblemJuggernaut` \| `DA_18_EmblemLunar` \| `DA_18_EmblemPrimal` \| `DA_18_EmblemRapidfire` \| `DA_18_EmblemSlayer` \| `DA_18_EmblemSpellweaver` \| `DA_18_EmblemSprykin` \| `DA_18_EmblemVanguard` \| `DA_AdaptiveHelm` \| `DA_AdaptiveHelm_Radiant` \| `DA_ArchangelsStaff` \| `DA_ArchangelsStaffRadiant` \| `DA_Artifact_AegisOfDawn` \| `DA_Artifact_AegisOfDusk` \| `DA_Artifact_BlightingJewel` \| `DA_Artifact_Dawncore` \| `DA_Artifact_EternalPact` \| `DA_Artifact_Fishbones` \| `DA_Artifact_ForbiddenIdol` \| `DA_Artifact_GamblersBlade` \| `DA_Artifact_GoldCollector` \| `DA_Artifact_HellfireHatchet` \| `DA_Artifact_HorizonFocus` \| `DA_Artifact_InfinityForce` \| `DA_Artifact_LichBane` \| `DA_Artifact_LightshieldCrest` \| `DA_Artifact_LudensTempest` \| `DA_Artifact_Manazane` \| `DA_Artifact_Mittens` \| `DA_Artifact_MogulsMail` \| `DA_Artifact_NavoriFlickerblade` \| `DA_Artifact_RapidFireCannon` \| `DA_Artifact_SeekersArmguard` \| `DA_Artifact_SilvermereDawn` \| `DA_Artifact_StatikkShiv` \| `DA_Artifact_TheIndomitable` \| `DA_Artifact_TitanicHydra` \| `DA_Artifact_VoidGauntlet` \| `DA_Artifact_WitsEnd` \| `DA_Artifact_ZhonyasParadox` \| `DA_BlastPotion18` \| `DA_BlastPotion18_Radiant` \| `DA_Bloodthirster` \| `DA_BloodthirsterRadiant` \| `DA_BlueBuff` \| `DA_BlueBuffRadiant` \| `DA_BrambleVest` \| `DA_BrambleVestRadiant` \| `DA_Component_BFSword` \| `DA_Component_ChainVest` \| `DA_Component_FryingPan` \| `DA_Component_GiantsBelt` \| `DA_Component_NeedlesslyLargeRod` \| `DA_Component_NegatronCloak` \| `DA_Component_RecurveBow` \| `DA_Component_SparringGloves` \| `DA_Component_Spatula` \| `DA_Component_TearOfTheGoddess` \| `DA_Crownguard` \| `DA_CrownguardRadiant` \| `DA_Deathblade` \| `DA_DeathbladeRadiant` \| `DA_DragonsClaw` \| `DA_DragonsClawRadiant` \| `DA_EdgeOfNight` \| `DA_EdgeOfNightRadiant` \| `DA_Evenshroud` \| `DA_EvenshroudRadiant` \| `DA_GargoyleStoneplate` \| `DA_GargoyleStoneplate_Radiant` \| `DA_GiantSlayer` \| `DA_GiantSlayer_Radiant` \| `DA_GuinsoosRageblade` \| `DA_GuinsoosRagebladeRadiant` \| `DA_HandOfJustice` \| `DA_HandOfJusticeRadiant` \| `DA_HealthPotion18` \| `DA_HealthPotion18_Radiant` \| `DA_HextechGunblade` \| `DA_HextechGunbladeRadiant` \| `DA_InfinityEdge` \| `DA_InfinityEdgeRadiant` \| `DA_IonicSpark` \| `DA_IonicSparkRadiant` \| `DA_Item_Artifact_TalismanOfAscension` \| `DA_JeweledGauntlet` \| `DA_JeweledGauntletRadiant` \| `DA_KrakensFury` \| `DA_KrakensFury_Radiant` \| `DA_LastWhisper` \| `DA_LastWhisperRadiant` \| `DA_ManaPotion18` \| `DA_ManaPotion18_Radiant` \| `DA_Morellonomicon` \| `DA_MorellonomiconRadiant` \| `DA_NashorsTooth` \| `DA_NashorsToothRadiant` \| `DA_ProtectorsVow` \| `DA_ProtectorsVowRadiant` \| `DA_Quicksilver` \| `DA_QuicksilverRadiant` \| `DA_RabadonsDeathcap` \| `DA_RabadonsDeathcap_Radiant` \| `DA_RedBuff` \| `DA_RedBuffRadiant` \| `DA_SpearOfShojin` \| `DA_SpearOfShojinRadiant` \| `DA_SpiritVisage` \| `DA_SpiritVisage_Radiant` \| `DA_SteadfastHeart` \| `DA_SteadfastHeartRadiant` \| `DA_SteraksGage` \| `DA_SteraksGageRadiant` \| `DA_StrikersFlail` \| `DA_StrikersFlailRadiant` \| `DA_SunfireCape` \| `DA_SunfireCape_Radiant` \| `DA_TacticiansCape` \| `DA_TacticiansCrown` \| `DA_TacticiansShield` \| `DA_ThiefsGloves` \| `DA_ThiefsGlovesRadiant` \| `DA_TitansResolve` \| `DA_TitansResolve_Radiant` \| `DA_VoidStaff` \| `DA_VoidStaffRadiant` \| `DA_WarmogsArmor` \| `DA_WarmogsArmorRadiant` | TFT item ID (e.g., TFT17_AnimaSquadItem_Tier1_RocketSwarm) to get cham |

---

## `tft_list_item_combinations`

> TFT tool for retrieving information about item combinations and recipes.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `lang` | string | 선택 | 기본값 `en_US` | Locale code |

---

## `tft_list_meta_decks`

> TFT deck list tool for retrieving current meta decks.

응답 형식: **JSON**

인자 없음

---

# 발로란트  (6개)

## `valorant_list_agent_compositions_for_map`

> Retrieve agent composition data for a Valorant map.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `map_id` | string | **필수** |  | Valorant map identifier (e.g., ascent, bind, lotus). |

---

## `valorant_list_agent_statistics`

> Retrieve character statistics data for Valorant, optionally filtered by map.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `map_id` | string | 선택 |  | Optional Valorant map identifier (e.g., ascent, bind). |

---

## `valorant_list_agents`

> Returns compact Valorant agent metadata with each agent name and two non-passive skill names localized across supported languages.

응답 형식: **JSON**

인자 없음

---

## `valorant_list_leaderboard`

> Fetch Valorant leaderboard by region

응답 형식: **압축**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `region` | string | **필수** | ap, br, eu |  |
| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | 받아올 필드 경로 |

<details><summary>출력 필드 목록</summary>

```
current_page
data[].badges[].{description,iconUrl,key,level,title,value}
data[].stat.{assists,bodyShots,deaths,defeats,draws,gameCount,headShots,kills,legShots,rounds,score,wins}
data[].{competitiveTier,gameName,leaderboardRank,level,mostCharacters[],numberOfWins,playerCardId,playerTitleId,puuid,rankedRating,tagLine}
from
lastUpdatedAt
last_page
per_page
to
total
```

</details>

---

## `valorant_list_maps`

> Retrieve compact Valorant map metadata for maps with agent composition data, including map IDs and localized map names across supported languages.

응답 형식: **JSON**

인자 없음

---

## `valorant_list_player_matches`

> Retrieve match history for a Valorant player using their game name and tag line.

응답 형식: **JSON**

| 인자 | 타입 | 필수 | 값 | 설명 |
|---|---|---|---|---|
| `game_name` | string | **필수** |  | Riot ID game name before the "#" (e.g., "Faker" from "Faker#KR1") |
| `tag_line` | string | **필수** |  | Riot ID tag line following the "#" (e.g., "KR1" from "Faker#KR1") |

---
