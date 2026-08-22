# -*- coding: utf-8 -*-
"""
차차차 컨텐츠 DB 9종 생성기.

스키마(키 이름/타입/열거값)는 Assembly-CSharp.dll 의 *DataBase::LoadDataBa*,
*::Build IL 에서 전부 복원한 것이라 원본과 동일하다.
반면 **수치는 원본이 아니다** — 2014년 CDN 과 함께 소실됐으므로 새로 설계했다.

설계 원칙
  - 등급 C(시작) -> B -> A -> S -> R 로 올라간다. eCarClassType 순서는 R,S,A,B,C 이고
    UpgradeCostDB 는 인덱스 4(C)를 건너뛰므로 "그 등급에 도달하는 비용"으로 해석했다.
  - 차량은 APK 로컬 Resources 에 실제로 들어 있는 car_01 ~ car_11 만 정의한다.
    (CDN 에만 있던 나머지 차량은 모델이 없어 정의해도 렌더링되지 않는다.)
  - 허들 Type 은 eHurdleType, 아이템 등급은 eItemGrade 처럼 열거형 멤버 이름을
    문자열로 그대로 쓴다. StrToEnum 이 ((enum)i).ToString() 과 문자열 비교를 하기 때문.
"""
import json, os, io

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
CLASSES = ["C", "B", "A", "S", "R"]          # 낮은 등급 -> 높은 등급
CLASS_STEP = {"C": 0, "B": 1, "A": 2, "S": 3, "R": 4}
TURNING = ["Accel", "Speed", "Oil"]
TURN_LV = 10                                  # 튜닝 단계 수

CARS = [
    # (index, 이름, 시작등급, 해금트로피, 골드가, 프리미엄, 로봇)
    (1,  "CAR_01", "C",     0,      0, False, False),
    (2,  "CAR_02", "C",    50,  12000, False, False),
    (3,  "CAR_03", "C",   150,  30000, False, False),
    (4,  "CAR_04", "B",   400,  70000, False, False),
    (5,  "CAR_05", "B",   800, 150000, False, False),
    (6,  "CAR_06", "B",  1400, 260000, False, False),
    (7,  "CAR_07", "A",  2200, 420000, False, False),
    (8,  "CAR_08", "A",  3200, 650000, False, False),
    (9,  "CAR_09", "A",  4500, 950000, True,  False),
    (10, "CAR_10", "S",  6000,      0, True,  False),
    (11, "CAR_11", "S",  8000,      0, True,  False),
]


def car_class_stats(idx, cls):
    """차량 인덱스와 등급으로 주행 스탯을 만든다. 등급이 오를수록 전 스탯이 향상된다."""
    s = CLASS_STEP[cls]
    return {
        "CarClassType": cls,
        "CarWeight": 900 + idx * 35 + s * 20,
        "MaxSpeed": round(118.0 + idx * 5.5 + s * 9.0, 2),
        "SpeedPerSecond": round(17.0 + idx * 0.55 + s * 1.4, 2),
        "NextStepSpeed": round(150.0 + idx * 6.0 + s * 11.0, 2),
        "NextSpeedPerSecond": round(9.0 + idx * 0.35 + s * 0.9, 2),
        "OilMileage": round(1.00 + s * 0.06 - idx * 0.012, 3),
    }


def car_entry(idx, name, start_cls, trophy, gold, premium, robot):
    return {
        "CarName": name,
        "CarIndex": idx,
        "StartCarClassType": start_cls,
        "CostGold": gold,
        "UnlockTrophy": trophy,
        "Preminum": premium,                 # 원본 오타 그대로 (Premium 아님)
        "NewCar": idx >= 10,
        "EventCar": False,
        "RivalCar": False,
        "IsRobot": robot,
        "HasMission": idx <= 6,
        "IsViewStore": gold > 0,
        "IsPossibleTradeCar": not premium,
        "MissionType": "mission%d" % idx if idx <= 6 else "none",
        "IsGotyaEvent": premium,
        "GotyaCost": 300 if premium else 0,
        "GotyaRetryCost": 150 if premium else 0,
        "CarIconAtlas": "Atlas_MainMenu",
        "OriginalSkill": 1 + (idx % 6),
        "SynergyDriver": 0,
        "IsEffectByClass": True,
        "IsAnotherNitro": premium,
        "BossConnectIndex": 0,
        # 시작 등급 이상만 정의한다 (C 시작차는 C~R 전부, S 시작차는 S,R 만)
        "CarClassDataArray": [car_class_stats(idx, c)
                              for c in CLASSES[CLASS_STEP[start_cls]:]],
    }


def turning_cost(cls, ttype):
    """튜닝 1~10단계 비용. 등급이 높을수록, 단계가 올라갈수록 비싸진다."""
    base = {"Accel": 800, "Speed": 1000, "Oil": 600}[ttype]
    mul = 1 + CLASS_STEP[cls] * 0.9
    return [int(base * mul * (1.55 ** i)) for i in range(TURN_LV)]


def car_database():
    return {"CarDataBase": {
        # 튜닝 1단계당 오르는 수치
        "TurningStatusDB": {
            "MaxSpeed": 1.6, "SpeedPerSecond": 0.32,
            "NextStepSpeed": 1.9, "NextSpeedPerSecond": 0.22,
            "OilMileage": 0.018,
        },
        # 해당 등급으로 승급하는 비용 (C 는 시작 등급이라 없음)
        "UpgradeCostDB": {"B": 6000, "A": 28000, "S": 130000, "R": 520000},
        "TurningCostDB": {"CarClassDataArray": [
            {"CarClassType": c,
             "TurningTypeDataArray": [{"TurningType": t, "CostArray": turning_cost(c, t)}
                                      for t in TURNING]}
            for c in CLASSES]},
        "CarInfoDB": {"CarDataArray": [car_entry(*c) for c in CARS]},
    }}


def driver_database():
    """드라이버 8종. 시너지/보조 능력치 위주."""
    out = []
    for i in range(1, 9):
        out.append({
            "ServerIndex": i,
            "DriverIndex": i,
            "DriverCost": 0 if i == 1 else 20000 * i,
            "hidden": False,
            "random": i > 5,
            "isVisibleStore": i > 1,
            "DriverName": "Driver_%02d" % i,
            "MagnetLength": round(1.0 + i * 0.15, 2),
            "CrashPenaltyFactor": round(1.0 - i * 0.03, 3),
            "SubOilCount": i // 3,
            "SubOilType": 0,
            "LimitBumperCount": 3 + i // 2,
            "BumperCount": 1 + i // 4,
            "AddTotalScoreMin": 100 * i,
            "AddTotalScoreMax": 300 * i,
            "GoldGainFactor": round(1.0 + i * 0.05, 3),
            "AddSkillLevel": i // 4,
            "isTrade": i > 2,
            "tradeCost": 5000 * i,
            "synergyCarIndex": i if i <= len(CARS) else 0,
            "synergyType": 0,
            "synergyValue": round(0.05 * i, 3),
        })
    return {"DriverDataBase": {"DriverDataArray": out}}


MAIN_OPTIONS = ["BladeWheel", "BullHornBumper", "ChaChaCombo", "HyperBooster",
                "MoneyScore", "AddWeight", "MachineGun", "RocketDamage",
                "GetDoubleStar", "AddAccelspeed"]
SUB_OPTIONS = ["RivalScore", "DriveScore", "ChaChaScore", "GoldScore", "CrashReduce",
               "LastCha", "ItemAddTime", "AddLimitSpeed", "FrontSensor", "AccelerateTime",
               "AddBumper", "BumperRateUp", "ShadowRateUp", "MagnetRateUp", "BoosterRateUp"]
GRADES = ["C", "B", "A", "S"]


def equip_database():
    items = []
    idx = 1
    for gi, grade in enumerate(GRADES):
        for mi, mo in enumerate(MAIN_OPTIONS):
            items.append({
                "IsNewItem": False,
                "Index": idx,
                "NameCode": "EquipItem_%s_%s" % (grade, mo),
                "ItemGrade": grade,
                "IconFileName": "Item_%s" % mo,
                # 원본은 SubOptionID_1 을 두 번 읽는 버그가 있어 _2 는 쓰이지 않는다
                "SubOptionID_1": 1 + (idx % len(SUB_OPTIONS)),
                "MainOptionDB": {
                    "Index": mi + 1,
                    "NameCode": "MainOption_%s" % mo,
                    "MainOptionType": mo,
                    "SkillType": "Passive",
                    "UnitType": "Rate",
                    "BaseVal": round(0.05 + gi * 0.03, 3),
                    "GradeVal": round(0.02 * (gi + 1), 3),
                    "ReinforceVal": round(0.006 * (gi + 1), 4),
                    "DurationVal": round(2.0 + gi * 0.5, 2),
                    "DescriptionCode": "MainOptionDesc_%s" % mo,
                },
            })
            idx += 1
    return {
        "EquipItemDataArray": items,
        "SellCostDB": {"S": 12000, "A": 5000, "B": 1800, "C": 600},
        "EquipItemCost": {"GotchaGold": 30000, "GotchaTrophy": 30,
                          "ExtendInven": 15000, "ExtendSlot": 50},
    }


def suboption_database():
    return {"EquipItemSubOptionArray": [
        {"Index": i + 1, "SubOptionType": so, "UnitType": "Rate",
         "OptionVal": round(0.03 + (i % 5) * 0.015, 4)}
        for i, so in enumerate(SUB_OPTIONS)]}


SKILL_ABILITIES = [
    ("SubOilCount", "Count", 1.0), ("OilConsumeFactor", "Rate", 0.08),
    ("AccelAddFactor", "Rate", 0.10), ("CrashPenaltyFactor", "Rate", 0.07),
    ("MagnetLength", "Rate", 0.12), ("GoldGainFactor", "Rate", 0.09),
    ("MaxSpeedFactor", "Rate", 0.06), ("BumperCount", "Count", 1.0),
    ("ItemKeepDuration", "Second", 0.8), ("LastNitroDuration", "Second", 0.6),
    ("HandlingFactor", "Rate", 0.08), ("AddTotalScoreMin", "Count", 120.0),
]


def skill_database():
    skills = []
    for i, (ab, unit, base) in enumerate(SKILL_ABILITIES, start=1):
        active = (i % 4 == 0)
        skills.append({
            "IsNewSkill": False,
            "Index": i,
            "NameCode": "Skill_%s" % ab,
            "SkillType": "Active" if active else "Passive",
            "SlotType": "Origin" if i <= 4 else ("Addtion" if i <= 8 else "Other"),
            "MaxLevel": 5,
            "BuyCost": {"CostType": "Gold", "Cost": 8000 * i},
            "UpgradeCost": [int(4000 * i * (1.7 ** lv)) for lv in range(5)],
            "IconFileName": "Skill_%02d" % i,
            "DescriptionCode": "SkillDesc_%s" % ab,
            "EffectFileName": "",
            "ActionData": {"ActionResultArray": [{
                "AbilityType": ab,
                "va_TotalFactor": round(base * 5, 4),
                "va_Base": round(base, 4),
                "va_LvFactor": round(base * 0.25, 4),
                "UnitType": unit,
            }]},
        })
    return {"SkillDataArray": skills}


HURDLES = ["Cone", "OilSpot", "SmallWall", "ParkingCar",
           "TroubleCar", "DangerMark", "Jewel", "JewelSmall"]
TRACK_DISTANCE = 10000


def hurdle_database():
    """3개 섹션 x 각 24개 장애물. Position 은 반드시 CommonData.Distance 미만이어야 한다."""
    sections = []
    for sid in range(1, 4):
        group = []
        for k in range(24):
            pos = 300 + k * 380 + sid * 60
            if pos >= TRACK_DISTANCE:
                break
            h = HURDLES[(k + sid) % len(HURDLES)]
            group.append({
                "Type": h,
                "Position": pos,
                "RotateY": 0,
                "Layer": 0,
                "LaneArray": [(k + sid) % 3],
            })
        sections.append({"SectionID": sid, "HurdleDataGroup": group})
    return {"HurdleDB": {
        "CommonData": {"Distance": TRACK_DISTANCE, "LoopCount": 3, "RewindSectionID": 1},
        "HurdleSectionGroup": sections,
    }}


def map_database():
    """ThemeName / TunnelList 항목은 GetResourceGameObject 로 로드되므로
       APK 로컬 Resources 에 실제로 있는 이름(Background)만 쓴다."""
    theme = {"ThemeName": "Background", "LoopCount": 3}
    return {
        "BackgroundPublic": {"ThemeList": [theme], "TunnelList": ["Background"]},
        "BackgroundHurdle": {"ThemeList": [theme], "TunnelList": ["Background"]},
        "BackgroundTimeAttack": {"ThemeList": [dict(theme, LoopCount=1)],
                                 "TunnelList": ["Background"]},
    }


def boss_database():
    bosses = []
    for i in range(1, 6):
        bosses.append({
            "BossName": "Boss_%02d" % i,
            "BossIndex": i,
            "AppearType": 0,
            "AttackType": i % 3,
            "SkillType": i % 3,
            "BossHP": [8000 * i * (lv + 1) for lv in range(5)],
            "AttackCooltime": [max(2, 6 - lv) for lv in range(5)],
            "AttackDamage": [40 * i + 12 * lv for lv in range(5)],
            "SkillCooltime": [max(5, 14 - lv) for lv in range(5)],
            "SkillDamage": [90 * i + 25 * lv for lv in range(5)],
            "Shield": 300 * i,
            "IsMoveBoss": i % 2 == 0,
            "IsAttackMotion": True,
            "ShieldCooltime": 12.0,
            "UnlockRewardCar": min(i + 6, len(CARS)),
        })
    return {"BossDataBase": {
        "WeaponDB": {"WeaponInfo": [
            {"Name": "Weapon_Missile", "Index": 1, "Damage": 120},
            {"Name": "Weapon_Gatling_Gun", "Index": 2, "Damage": 45},
        ]},
        "CloneDB": {
            "MaxCloneCount": 4,
            "CloneInfo": [{"Level": lv + 1, "SpeedMin": 90 + lv * 8, "SpeedMax": 120 + lv * 10}
                          for lv in range(5)],
            "CloneDisposition": [{"StartType": 0, "EndType": 1,
                                  "CloneDistance": [400, 800, 1200, 1600]}],
        },
        "BossDB": {
            "BossAccountInfo": {"BossStartIndex": 1, "BossCount": len(bosses),
                                "StartStage": 1, "NextStage": 2},
            "BossCommonInfo": {"UnlockBonusMin": 500, "UnlockBonusMax": 2000,
                               "FireWallSpeed": 22.0, "LaserMaintainTime": 3.5},
            "BossInfo": bosses,
        },
    }}


def timeattack_database():
    rows = [("S", 30000, 0, 60), ("A", 15000, 60, 90), ("B", 7000, 90, 120),
            ("C", 3000, 120, 180), ("D", 1000, 180, 999999)]
    return {"TimeAttackRankDB": {"TimeAttackRankDataArray": [
        {"grade": g, "prize": p, "underTime": u, "overTime": o} for g, p, u, o in rows]}}


DBS = {
    "CarDataBase": car_database,
    "DriverDataBase": driver_database,
    "EquipItemDataBase": equip_database,
    "EquipItemSubOptionDB": suboption_database,
    "SkillDB": skill_database,
    "HurdleDB": hurdle_database,
    "MapDB": map_database,
    "BossDataBase": boss_database,
    "TimeAttackRankDB": timeattack_database,
}

if __name__ == "__main__":
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    total = 0
    for name, fn in sorted(DBS.items()):
        blob = json.dumps(fn(), ensure_ascii=False, separators=(',', ':'))
        io.open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8").write(blob)
        total += len(blob)
        print("  %-24s %8d 자" % (name, len(blob)))
    print("  합계 %d 자 / %d개" % (total, len(DBS)))
