# -*- coding: utf-8 -*-
"""扩充歌库：Hamilton 全剧 + 同类高词汇密度音乐剧整专 + 叙事流行扩充。
复用 fetch_lyrics 的抓取/清洗逻辑，只抓新增曲目，保存到 歌词/，文件名带前缀 H/P/M...
"""
import os, time, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_lyrics import get_one, OUT  # 复用同一抓取函数与歌词目录

# (key, 艺人, 曲目)；Hamilton 用原卡司常见演唱者，检索失败会自动 search 兜底
NEW_SONGS = []

# —— Hamilton 全剧（含此前 7 首之外的其余曲目，前缀 H）——
HAM_ARTIST = "Lin-Manuel Miranda"
hamilton_tracks = [
    ("H01_AaronBurrSir", "Leslie Odom Jr.", "Aaron Burr, Sir"),
    ("H02_MyShot", "Lin-Manuel Miranda", "My Shot"),
    ("H03_StoryOfTonight", "Anthony Ramos", "The Story of Tonight"),
    ("H04_SchuylerSisters", "Renée Elise Goldsberry", "The Schuyler Sisters"),
    ("H05_FarmerRefuted", "Thayne Jasperson", "Farmer Refuted"),
    ("H06_YoullBeBack", "Jonathan Groff", "You'll Be Back"),
    ("H07_RightHandMan", "Christopher Jackson", "Right Hand Man"),
    ("H08_WinterBall", "Lin-Manuel Miranda", "A Winter's Ball"),
    ("H09_Helpless", "Phillipa Soo", "Helpless"),
    ("H10_Satisfied", "Renée Elise Goldsberry", "Satisfied"),
    ("H11_StoryTonightReprise", "Anthony Ramos", "The Story of Tonight (Reprise)"),
    ("H12_WaitForIt", "Leslie Odom Jr.", "Wait for It"),
    ("H13_StayAlive", "Lin-Manuel Miranda", "Stay Alive"),
    ("H14_TenDuelCommandments", "Anthony Ramos", "Ten Duel Commandments"),
    ("H15_MeetMeInside", "Lin-Manuel Miranda", "Meet Me Inside"),
    ("H16_ThatWouldBeEnough", "Phillipa Soo", "That Would Be Enough"),
    ("H17_GunsAndShips", "Daveed Diggs", "Guns and Ships"),
    ("H18_HistoryHasItsEyes", "Christopher Jackson", "History Has Its Eyes on You"),
    ("H19_Yorktown", "Lin-Manuel Miranda", "Yorktown (The World Turned Upside Down)"),
    ("H20_WhatComesNext", "Jonathan Groff", "What Comes Next?"),
    ("H21_DearTheodosia", "Leslie Odom Jr.", "Dear Theodosia"),
    ("H22_NonStop", "Lin-Manuel Miranda", "Non-Stop"),
    ("H23_WhatdIMiss", "Daveed Diggs", "What'd I Miss"),
    ("H24_CabinetBattle1", "Daveed Diggs", "Cabinet Battle #1"),
    ("H25_TakeABreak", "Renée Elise Goldsberry", "Take a Break"),
    ("H26_SayNoToThis", "Jasmine Cephas Jones", "Say No to This"),
    ("H27_AppalachianSnow", "Leslie Odom Jr.", "The Room Where It Happens"),
    ("H28_SchuylerDefeated", "Phillipa Soo", "Schuyler Defeated"),
    ("H29_CabinetBattle2", "Okieriete Onaodowan", "Cabinet Battle #2"),
    ("H30_WashingtonOnYourSide", "Daveed Diggs", "Washington on Your Side"),
    ("H31_OneLastTime", "Christopher Jackson", "One Last Time"),
    ("H32_KnowYourEnemy", "Jonathan Groff", "I Know Him"),
    ("H33_AdamstheAdministration", "Leslie Odom Jr.", "The Adams Administration"),
    ("H34_WeKnow", "Lin-Manuel Miranda", "We Know"),
    ("H35_Hurricane", "Lin-Manuel Miranda", "Hurricane"),
    ("H36_ReynoldsPamphlet", "Lin-Manuel Miranda", "The Reynolds Pamphlet"),
    ("H37_Burn", "Phillipa Soo", "Burn"),
    ("H38_BlowUsAllAway", "Anthony Ramos", "Blow Us All Away"),
    ("H39_StayAliveReprise", "Anthony Ramos", "Stay Alive (Reprise)"),
    ("H40_ItsQuietUptown", "Lin-Manuel Miranda", "It's Quiet Uptown"),
    ("H41_ElectionOf1800", "Leslie Odom Jr.", "The Election of 1800"),
    ("H42_YourObedientServant", "Lin-Manuel Miranda", "Your Obedient Servant"),
    ("H43_BestOfWivesBestOfWomen", "Lin-Manuel Miranda", "Best of Wives and Best of Women"),
    ("H44_WorldWasWideEnough", "Lin-Manuel Miranda", "The World Was Wide Enough"),
    ("H45_WhoLivesWhoDies", "Lin-Manuel Miranda", "Who Lives, Who Dies, Who Tells Your Story"),
]
NEW_SONGS += hamilton_tracks

# —— 同类音乐剧扩充（前缀 M）——
musicals = [
    # 悲惨世界 更多曲目
    ("M01_ICDreamedADream", "Les Misérables", "I Dreamed a Dream"),
    ("M02_OnMyOwn", "Les Misérables", "On My Own"),
    ("M03_Stars", "Les Misérables", "Stars"),
    ("M04_BringHimHome", "Les Misérables", "Bring Him Home"),
    ("M05_MasterOfTheHouse", "Les Misérables", "Master of the House"),
    ("M06_EmptyChairs", "Les Misérables", "Empty Chairs at Empty Tables"),
    # 马戏之王 其余
    ("M07_NeverEnough", "The Greatest Showman", "Never Enough"),
    ("M08_FromNowOn", "The Greatest Showman", "From Now On"),
    ("M09_RewriteTheStars", "The Greatest Showman", "Rewrite the Stars"),
    ("M10_Tightrope", "The Greatest Showman", "Tightrope"),
    # 致埃文汉森 其余
    ("M11_ForForever", "Dear Evan Hansen", "For Forever"),
    ("M12_WavingThroughWindow", "Dear Evan Hansen", "Waving Through a Window"),
    ("M13_OnlyUs", "Dear Evan Hansen", "Only Us"),
    # 魔法黑森林 / 吉屋出租 / 其他名剧
    ("M14_IntoTheWoodsPrologue", "Into the Woods", "Prologue: Into the Woods"),
    ("M15_ChildrenWillListen", "Into the Woods", "Children Will Listen"),
    ("M16_DefyingGravity", "Wicked", "Defying Gravity"),
    ("M17_Popular", "Wicked", "Popular"),
    ("M18_ForGood", "Wicked", "For Good"),
    ("M19_OneSongGlory", "Rent", "One Song Glory"),
    ("M20_LightMyCandle", "Rent", "Light My Candle"),
    ("M21_IllCoverYou", "Rent", "I'll Cover You"),
    ("M22_LaVieBoheme", "Rent", "La Vie Boheme"),
    ("M23_Memory", "Cats", "Memory"),
    ("M24_TheMusicOfTheNight", "The Phantom of the Opera", "The Music of the Night"),
    ("M25_ThinkOfMe", "The Phantom of the Opera", "Think of Me"),
    ("M26_CircleOfLife", "The Lion King", "Circle of Life"),
    ("M27_HakunaMatata", "The Lion King", "Hakuna Matata"),
    ("M28_BeOurGuest", "Beauty and the Beast", "Be Our Guest"),
    ("M29_SomethingThere", "Beauty and the Beast", "Something There"),
    ("M30_PartOfYourWorld", "The Little Mermaid", "Part of Your World"),
    ("M31_UnderTheSea", "The Little Mermaid", "Under the Sea"),
]
NEW_SONGS += musicals

# —— 叙事/高词汇流行扩充（前缀 P）——
pops = [
    ("P01_DriverLicense", "Olivia Rodrigo", "drivers license"),
    ("P02_Vienna", "Billy Joel", "Vienna"),
    ("P03_LostBoy", "Ruth B.", "Lost Boy"),
    ("P04_SevenNationArmy", "The White Stripes", "Seven Nation Army"),
    ("P05_Believer", "Imagine Dragons", "Believer"),
    ("P06_Thunder", "Imagine Dragons", "Thunder"),
    ("P07_HallOfFame", "The Script", "Hall of Fame"),
    ("P08_TheMan", "Taylor Swift", "The Man"),
    ("P09_ShakeItOff", "Taylor Swift", "Shake It Off"),
    ("P10_LoveStory", "Taylor Swift", "Love Story"),
    ("P11_DefaultDancing", "Ben Platt", "Grow As We Go"),
    ("P12_CastleOnTheHill", "Ed Sheeran", "Castle on the Hill"),
    ("P13_LegoHouse", "Ed Sheeran", "Lego House"),
    ("P14_Firework", "Katy Perry", "Firework"),
    ("P15_Roar", "Katy Perry", "Roar"),
    ("P16_Brave", "Sara Bareilles", "Brave"),
    ("P17_ItsTime", "Imagine Dragons", "It's Time"),
    ("P18_Demons", "Imagine Dragons", "Demons"),
    ("P19_Home", "Phillip Phillips", "Home"),
    ("P20_IWasHere", "Beyonce", "I Was Here"),
]
NEW_SONGS += pops

def main():
    miss=[]; got=0
    for key, artist, track in NEW_SONGS:
        path=os.path.join(OUT, key+".txt")
        if os.path.exists(path):
            print(f"skip {key} (exists)"); got+=1; continue
        lyr, src = get_one(artist, track)
        if lyr:
            open(path,"w",encoding="utf-8").write(lyr); got+=1
            print(f"OK  {key:26s} {len(lyr):6d}  {src[:70]}")
        else:
            miss.append((key,artist,track))
            print(f"MISS {key:26s} {artist} / {track}")
        time.sleep(0.35)
    print(f"\n新增曲目 {len(NEW_SONGS)}，成功 {got}，缺失 {len(miss)}")
    for k,a,t in miss: print("  MISS:",k,a,t)

if __name__=="__main__":
    main()
