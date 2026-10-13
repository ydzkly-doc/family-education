# -*- coding: utf-8 -*-
"""从 lrclib.net 抓取真实歌词（plainLyrics，纯文本）。
策略：先 /api/get 精确取；取不到则 /api/search 选最佳（优先纯歌词非器乐、长度合理）。
保存到 歌词/<key>.txt，并生成 抓取结果报告（含长度/来源，便于人工抽查）。
"""
import os, re, time, json, requests

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "歌词")
os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "songvocab-edu/1.0 (personal vocabulary study)"}

# key: (显示名, 艺人, 曲目)；艺人给多个候选以提高命中率
SONGS = [
    # —— 圈层 A Hamilton（原卡司）——
    ("A1_WaitForIt",        "Leslie Odom Jr.", "Wait For It"),
    ("A2_MyShot",           "Lin-Manuel Miranda", "My Shot"),
    ("A3_AlexanderHamilton","Lin-Manuel Miranda", "Alexander Hamilton"),
    ("A4_Helpless",         "Phillipa Soo", "Helpless"),
    ("A5_SchuylerSisters",  "Renée Elise Goldsberry", "The Schuyler Sisters"),
    ("A6_Satisfied",        "Renée Elise Goldsberry", "Satisfied"),
    ("A7_NonStop",          "Lin-Manuel Miranda", "Non-Stop"),
    # —— 圈层 B 音乐剧 ——
    ("B1_DoYouHear",        "Les Misérables", "Do You Hear the People Sing"),
    ("B2_OneDayMore",       "Les Misérables", "One Day More"),
    ("B3_MillionDreams",    "The Greatest Showman", "A Million Dreams"),
    ("B4_ThisIsMe",         "The Greatest Showman", "This Is Me"),
    ("B5_YouWillBeFound",   "Dear Evan Hansen", "You Will Be Found"),
    ("B6_SeasonsOfLove",    "Rent", "Seasons of Love"),
    ("B7_NoOneIsAlone",     "Into the Woods", "No One Is Alone"),
    # —— 圈层 C 迪士尼 ——
    ("C1_HowFarIllGo",      "Auli'i Cravalho", "How Far I'll Go"),
    ("C2_LetItGo",          "Idina Menzel", "Let It Go"),
    ("C3_SurfacePressure",  "Jessica Darrow", "Surface Pressure"),
    ("C4_WeDontTalkBruno",  "Encanto", "We Don't Talk About Bruno"),
    ("C5_Reflection",       "Mulan", "Reflection"),
    ("C6_WholeNewWorld",    "Aladdin", "A Whole New World"),
    # —— 圈层 D 叙事流行 ——
    ("D1_TheNights",        "Avicii", "The Nights"),
    ("D2_SevenYears",       "Lukas Graham", "7 Years"),
    ("D3_PianoMan",         "Billy Joel", "Piano Man"),
    ("D4_CatsInCradle",     "Harry Chapin", "Cat's in the Cradle"),
    # —— 12周入门流行（基础高频，校准用）——
    ("E1_LemonTree",        "Fools Garden", "Lemon Tree"),
    ("E2_TryEverything",    "Shakira", "Try Everything"),
    ("E3_BigBigWorld",      "Emilia", "Big Big World"),
    ("E4_YesterdayOnceMore","Carpenters", "Yesterday Once More"),
    ("E5_HeyJude",          "The Beatles", "Hey Jude"),
    ("E6_LetItBe",          "The Beatles", "Let It Be"),
    ("E7_YouRaiseMeUp",     "Westlife", "You Raise Me Up"),
    ("E8_CountOnMe",        "Bruno Mars", "Count On Me"),
    ("E9_TroubleFriend",    "Lenka", "Trouble Is a Friend"),
    ("E10_Try",             "Colbie Caillat", "Try"),
    ("E11_TheShow",         "Lenka", "The Show"),
]

def clean_lyrics(t):
    if not t:
        return ""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # 去 时间戳（同步歌词残留）与常见广告行
    t = re.sub(r"\[\d{1,2}:\d{2}(\.\d{2,3})?\]", "", t)
    lines = [ln.strip() for ln in t.split("\n")]
    lines = [ln for ln in lines if ln and "lyrics" not in ln.lower()[:12]
             and not re.match(r"^(translations?|contributors?|thanks)\b", ln, re.I)]
    return "\n".join(lines)

def get_one(artist, track):
    # 精确
    try:
        r = requests.get("https://lrclib.net/api/get",
                         params={"artist_name": artist, "track_name": track},
                         headers=H, timeout=20)
        if r.status_code == 200:
            j = r.json()
            lyr = j.get("plainLyrics") or j.get("syncedLyrics") or ""
            lyr = clean_lyrics(lyr)
            if lyr:
                return lyr, f"get:{j.get('artistName')}/{j.get('trackName')}(id={j.get('id')})"
    except Exception:
        pass
    time.sleep(0.5)
    # 搜索兜底
    try:
        r = requests.get("https://lrclib.net/api/search",
                         params={"track_name": track, "artist_name": artist},
                         headers=H, timeout=20)
        if r.status_code == 200 and r.json():
            best = None
            for j in r.json():
                lyr = clean_lyrics(j.get("plainLyrics") or j.get("syncedLyrics") or "")
                if not lyr:
                    continue
                # 偏好标题接近、纯英文、长度适中(>200)
                if best is None or len(lyr) > len(best[0]):
                    best = (lyr, j)
            if best:
                lyr, j = best
                return lyr, f"search:{j.get('artistName')}/{j.get('trackName')}(id={j.get('id')},len={len(lyr)})"
    except Exception:
        pass
    return "", ""

def main():
    report = []
    for key, artist, track in SONGS:
        lyr, src = get_one(artist, track)
        if lyr:
            with open(os.path.join(OUT, key + ".txt"), "w", encoding="utf-8") as f:
                f.write(lyr)
        report.append((key, artist, track, len(lyr), src or "*** MISS ***"))
        print(f"{key:22s} {len(lyr):6d}  {src or 'MISS'}")
        time.sleep(0.4)
    miss = [r for r in report if r[3] == 0]
    with open(os.path.join(BASE, "歌词抓取报告.json"), "w", encoding="utf-8") as f:
        json.dump([{"key": k, "artist": a, "track": t, "chars": c, "src": s}
                   for k, a, t, c, s in report], f, ensure_ascii=False, indent=2)
    print(f"\n共 {len(report)} 首，缺失 {len(miss)} 首")
    for k, a, t, c, s in miss:
        print("  MISS:", k, a, t)

if __name__ == "__main__":
    main()
