from users.models import User, Character, Stats
from secret_data import DM_PARAMS
import django

try:
    userDM = User.objects.get(username=DM_PARAMS["username"])
    if Character.objects.filter(user=userDM).exists():
        characterDM = Character.objects.get(user=userDM)
        statsDM = characterDM.stats
    else:
        statsDM = Stats(custom_class="DungeonMaster", custom_race="Master", level=0, stre=0, dex=0, cos=0, inte=0, wis=0, cha=0, stre_down=0, dex_down=0, cos_down=0, inte_down=0, wis_down=0, cha_down=0, proficiency_bonus=0, passive_perception=0, stre_saving=0, dex_saving=0, cos_saving=0, inte_saving=0, wis_saving=0, cha_saving=0, acrobatics=0, animals=0, arcana=0, athletics=0, deception=0, history=0, insight=0, intimidation=0, investigation=0, medicine=0, nature=0, perception=0, performance=0, persuasion=0, religion=0, sleightofhand=0, stealth=0, survival=0, proficiencies=0, current_hit=0, attacks_spellcasting="", equipment="", personality_traits="", ideals="", bonds="", flaws="", features_traits="", success=0, failure=0, armour=0, initiative=0, speed=0)
        statsDM.save()
        characterDM = Character(stats=statsDM, image="character_pics/dm.jpg", name="DungeonMaster", user=userDM)
        characterDM.save()
        print("DM character created")
except Exception:
    userDM, characterDM, statsDM = None, None, None
    print("Cannot import DM")